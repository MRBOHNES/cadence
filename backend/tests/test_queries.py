from datetime import timedelta

import pytest

from app import queries
from tests.conftest import NOW

H = timedelta(hours=1)


async def row_for(session, code: str) -> dict:
    return next(r for r in await queries.monitor_rows(session, NOW) if r["short_code"] == code)


async def test_uptime_percentage(session, seed):
    m = await seed.monitor("a")
    for i in range(10):
        seed.check(m, ago=timedelta(minutes=10 * (i + 1)), ok=i != 0)
    await seed.commit()
    row = await row_for(session, "a")
    assert row["uptime_24h"] == 90.0 and row["uptime_30d"] == 90.0


async def test_uptime_window_excludes_old_checks(session, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=H, ok=True)
    seed.check(m, ago=timedelta(days=2), ok=False)  # outside 24h, inside 30d
    seed.check(m, ago=timedelta(days=40), ok=False)  # outside 30d entirely
    await seed.commit()
    row = await row_for(session, "a")
    assert (row["uptime_24h"], row["uptime_30d"]) == (100.0, 50.0)


async def test_uptime_is_none_without_checks(session, seed):
    await seed.monitor("a")
    await seed.commit()
    row = await row_for(session, "a")
    assert row["uptime_30d"] is None and row["state"] == "unknown"


async def test_percentiles_use_continuous_interpolation(session, seed):
    m = await seed.monitor("a")
    for i in range(10):
        seed.check(m, ago=timedelta(minutes=5 * (i + 1)), latency=100 * (i + 1))
    await seed.commit()
    row = await row_for(session, "a")
    assert (row["p50_ms"], row["p95_ms"]) == (550.0, 955.0)


async def test_percentiles_ignore_failed_checks_without_latency(session, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=H, latency=200)
    seed.check(m, ago=2 * H, ok=False)  # timeout: no latency
    await seed.commit()
    assert (await row_for(session, "a"))["p50_ms"] == 200.0


@pytest.mark.parametrize(
    ("ok", "latency", "expected"),
    [(True, 120, "up"), (True, 501, "slow"), (True, 500, "up"), (False, None, "down")],
)
async def test_current_state_from_latest_check(session, seed, ok, latency, expected):
    m = await seed.monitor("a")
    seed.check(m, ago=H, ok=True, latency=100)  # older check must not matter
    seed.check(m, ago=timedelta(minutes=5), ok=ok, latency=latency)
    await seed.commit()
    assert (await row_for(session, "a"))["state"] == expected


@pytest.mark.parametrize(
    ("total", "failed", "slow", "status"),
    [(0, 0, 0, "no-data"), (100, 0, 0, "up"), (100, 0, 10, "up"), (100, 0, 60, "degraded"),
     (100, 1, 0, "degraded"), (100, 5, 0, "degraded"), (100, 6, 0, "down")],
)
def test_day_status_rules(total, failed, slow, status):
    assert queries.day_status(total, failed, slow) == status


async def test_daily_history_has_30_buckets_with_today_last(session, seed):
    m = await seed.monitor("a")
    for i in range(20):
        seed.check(m, ago=timedelta(minutes=10 * (i + 1)), ok=i != 0)  # 1 failure in 20 = 95% up
    await seed.commit()
    history = (await row_for(session, "a"))["history"]
    assert len(history) == 30
    assert history[:29] == ["no-data"] * 29
    assert history[-1] == "degraded"


async def test_latency_series_averages_within_bins(session, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=timedelta(minutes=10), latency=100)  # 11:50
    seed.check(m, ago=timedelta(minutes=8), latency=300)  # 11:52, same 5-minute bin
    seed.check(m, ago=timedelta(minutes=1), latency=400)  # 11:59
    await seed.commit()
    series = await queries.latency_series(session, m.id, "24h", NOW)
    assert [p["latency_ms"] for p in series["points"]] == [200.0, 400.0]


async def test_latency_series_range_limits_window(session, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=H, latency=100)
    seed.check(m, ago=timedelta(days=3), latency=900)
    await seed.commit()
    assert len((await queries.latency_series(session, m.id, "24h", NOW))["points"]) == 1
    assert len((await queries.latency_series(session, m.id, "7d", NOW))["points"]) == 2
