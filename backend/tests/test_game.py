from datetime import UTC, datetime, timedelta

import pytest

from app import game
from tests.conftest import NOW

D = timedelta(days=1)


# --- HP ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("uptime", "hp"),
    [(100.0, 10), (99.95, 10), (99.9, 9), (99.85, 9), (99.5, 5), (99.05, 1), (99.0, 0), (95.0, 0), (0.0, 0), (None, 0)],
)
def test_hp_formula(uptime, hp):
    assert game.hp_for(uptime) == hp


def test_hp_rounds_half_up_not_bankers():
    # 99.85 -> 8.5 blocks: banker's rounding would give 8, half-up gives 9.
    assert game.hp_for(99.85) == 9


# --- Streaks -------------------------------------------------------------------------------


def test_streak_without_incidents_counts_from_start():
    assert game.streaks([], NOW - 12 * D, NOW) == (12, 12)


def test_streak_resets_to_zero_while_incident_is_open():
    current, _ = game.streaks([(NOW - 2 * D, None)], NOW - 10 * D, NOW)
    assert current == 0


def test_streak_counts_from_last_resolution():
    current, best = game.streaks([(NOW - 6 * D, NOW - 5 * D)], NOW - 10 * D, NOW)
    assert (current, best) == (5, 5)


def test_best_streak_is_longest_gap():
    incidents = [(NOW - 30 * D, NOW - 29 * D), (NOW - 10 * D, NOW - 9 * D)]
    current, best = game.streaks(incidents, NOW - 40 * D, NOW)
    assert (current, best) == (9, 19)  # gap between the two incidents is 19 days


def test_overlapping_incidents_are_merged():
    incidents = [(NOW - 5 * D, NOW - 2 * D), (NOW - 4 * D, NOW - 3 * D)]
    assert game.streaks(incidents, NOW - 6 * D, NOW)[0] == 2


# --- Rank ----------------------------------------------------------------------------------


def test_rank_by_uptime_then_p50():
    rows = [
        {"id": 1, "uptime_30d": 99.0, "p50_ms": 50},
        {"id": 2, "uptime_30d": 100.0, "p50_ms": 300},
        {"id": 3, "uptime_30d": 100.0, "p50_ms": 120},
        {"id": 4, "uptime_30d": None, "p50_ms": None},
    ]
    game.rank_monitors(rows)
    assert {r["id"]: r["rank"] for r in rows} == {3: 1, 2: 2, 1: 3, 4: 4}


# --- Achievements (each rule against the real DB) -------------------------------------------


async def unlocked(session) -> dict[str, dict]:
    return {a["id"]: a for a in await game.achievements(session, NOW)}


async def test_all_locked_when_empty(session, seed):
    await seed.commit()
    assert not any(a["unlocked"] for a in (await unlocked(session)).values())


async def test_99_9_club_unlocks_with_three_good_monitors(session, seed):
    for code in ("a", "b", "c", "d"):
        m = await seed.monitor(code)
        seed.history(m, bad_at={0, 1, 2, 3, 4, 5} if code == "d" else None)
    await seed.commit()
    assert (await unlocked(session))["99_9_club"]["unlocked"]


async def test_99_9_club_locked_when_only_two_are_good(session, seed):
    for code in ("a", "b", "c"):
        m = await seed.monitor(code)
        seed.history(m, bad_at={0, 1, 2, 3, 4, 5, 6, 7} if code == "c" else None)
    await seed.commit()
    club = (await unlocked(session))["99_9_club"]
    assert not club["unlocked"] and club["progress"] == "2 / 3 SERVICES"


async def test_99_9_club_needs_all_when_fewer_than_three_monitors(session, seed):
    a, b = await seed.monitor("a"), await seed.monitor("b")
    seed.history(a)
    seed.history(b)
    await seed.commit()
    assert (await unlocked(session))["99_9_club"]["unlocked"]


async def test_99_9_club_locked_without_30_days_of_data(session, seed):
    seed.history(await seed.monitor("a"), days=3)
    await seed.commit()
    club = (await unlocked(session))["99_9_club"]
    assert not club["unlocked"] and "COLLECTING DATA" in club["progress"]


async def test_sub_100ms_unlocks_for_fast_monitor(session, seed):
    m = await seed.monitor("a")
    for i in range(5):
        seed.check(m, ago=timedelta(hours=i + 1), latency=80)
    await seed.commit()
    assert (await unlocked(session))["sub_100ms"]["unlocked"]


async def test_sub_100ms_locked_when_median_is_higher(session, seed):
    m = await seed.monitor("a")
    for i, latency in enumerate([50, 150, 160, 170, 180]):
        seed.check(m, ago=timedelta(hours=i + 1), latency=latency)
    await seed.commit()
    result = (await unlocked(session))["sub_100ms"]
    assert not result["unlocked"] and result["progress"] == "BEST P50 160 MS"


async def test_iron_wall_unlocks_without_5xx(session, seed):
    seed.history(await seed.monitor("a"), days=8)
    await seed.commit()
    assert (await unlocked(session))["iron_wall"]["unlocked"]


async def test_iron_wall_locked_by_recent_5xx(session, seed):
    m = await seed.monitor("a")
    seed.history(m, days=8)
    seed.check(m, ago=timedelta(days=2), ok=False, status=503)
    await seed.commit()
    result = (await unlocked(session))["iron_wall"]
    assert not result["unlocked"] and result["progress"] == "1 SERVER ERRORS IN 7D"


async def test_iron_wall_ignores_5xx_older_than_7_days(session, seed):
    m = await seed.monitor("a")
    seed.history(m, days=10)
    seed.check(m, ago=timedelta(days=9), ok=False, status=500)
    await seed.commit()
    assert (await unlocked(session))["iron_wall"]["unlocked"]


async def test_on_fire_unlocks_after_30_quiet_days(session, seed):
    seed.history(await seed.monitor("a", created_days_ago=40), days=35)
    await seed.commit()
    assert (await unlocked(session))["on_fire"]["unlocked"]


async def test_on_fire_progress_counts_days_since_incident(session, seed):
    m = await seed.monitor("a", created_days_ago=40)
    seed.incident(m, start_ago=11 * D, end_ago=10 * D)
    await seed.commit()
    result = (await unlocked(session))["on_fire"]
    assert not result["unlocked"] and result["progress"] == "10 / 30 DAYS"


async def test_perfect_month_unlocks_at_100_percent(session, seed):
    for code in ("a", "b"):
        seed.history(await seed.monitor(code))
    await seed.commit()
    assert (await unlocked(session))["perfect_month"]["unlocked"]


async def test_perfect_month_progress_when_one_service_failed(session, seed):
    for code in ("a", "b", "c"):
        seed.history(await seed.monitor(code), bad_at={3} if code == "c" else None)
    await seed.commit()
    result = (await unlocked(session))["perfect_month"]
    assert not result["unlocked"] and result["progress"] == "2 / 3 SERVICES"


async def test_unlocked_at_is_stable_across_evaluations(session, seed):
    seed.history(await seed.monitor("a"), days=8)
    await seed.commit()
    first = (await unlocked(session))["iron_wall"]["unlocked_at"]
    later = await game.achievements(session, NOW + timedelta(hours=5))
    assert first == NOW
    assert next(a for a in later if a["id"] == "iron_wall")["unlocked_at"] == first


async def test_enrich_monitors_adds_hp_streak_and_rank(session, seed):
    from app import queries

    m = await seed.monitor("a")
    seed.history(m, days=5)
    await seed.commit()
    rows = await game.enrich_monitors(session, await queries.monitor_rows(session, NOW), NOW)
    assert (rows[0]["hp"], rows[0]["rank"]) == (10, 1)
    assert rows[0]["streak_days"] >= 5
    assert isinstance(NOW, datetime) and NOW.tzinfo is UTC
