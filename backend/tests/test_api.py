from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Sweep
from tests.conftest import NOW

M = timedelta(minutes=1)


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


async def test_summary_shape_and_values(client, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=5 * M, latency=100)
    seed.check(m, ago=10 * M, ok=False)
    await seed.commit()
    body = (await client.get("/summary")).json()
    assert set(body) == {
        "uptime_30d", "uptime_change", "services_up", "services_total", "median_ms_24h",
        "median_change_ms", "p95_ms_24h", "p95_change_ms", "checks_24h", "failed_24h",
        "latest_sweep", "latest_sweep_at", "latest_sweep_duration_ms", "next_sweep_at", "streak_days", "best_streak_days", "open_incidents",
    }  # fmt: skip
    assert body["uptime_30d"] == 50.0
    assert (body["checks_24h"], body["failed_24h"]) == (2, 1)
    assert (body["services_up"], body["services_total"]) == (1, 1)
    assert body["latest_sweep"] == seed.sweep_id


async def test_summary_next_sweep_is_five_minutes_after_last(client, seed):
    await seed.monitor("a")
    await seed.commit()
    body = (await client.get("/summary")).json()
    assert body["next_sweep_at"] == (NOW - 2 * M + 5 * M).isoformat().replace("+00:00", "Z")


async def test_summary_change_vs_previous_period(client, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=timedelta(days=1), ok=True)  # current 30d: 100%
    seed.check(m, ago=timedelta(days=40), ok=True)
    seed.check(m, ago=timedelta(days=41), ok=False)  # previous 30d: 50%
    await seed.commit()
    assert (await client.get("/summary")).json()["uptime_change"] == 50.0


async def test_summary_counts_open_incidents_and_down_services(client, seed):
    a, b = await seed.monitor("a"), await seed.monitor("b")
    seed.check(a, ago=M)
    seed.check(b, ago=M, ok=False)
    seed.incident(b, start_ago=10 * M, end_ago=None)
    await seed.commit()
    body = (await client.get("/summary")).json()
    assert (body["open_incidents"], body["services_up"], body["services_total"]) == (1, 1, 2)


async def test_summary_with_empty_database(client):
    body = (await client.get("/summary")).json()
    assert body["uptime_30d"] is None and body["latest_sweep"] is None and body["next_sweep_at"] is None


async def test_monitors_shape(client, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=M)
    await seed.commit()
    [item] = (await client.get("/monitors")).json()
    assert set(item) == {
        "id", "name", "short_code", "url", "state", "uptime_24h", "uptime_30d", "p50_ms",
        "p95_ms", "history", "streak_days", "hp", "rank",
    }  # fmt: skip
    assert len(item["history"]) == 30 and item["state"] == "up"


async def test_latency_endpoint(client, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=M, latency=250)
    await seed.commit()
    body = (await client.get(f"/monitors/{m.id}/latency?range=7d")).json()
    assert body["range"] == "7d" and body["p50_ms"] == 250.0
    assert [p["latency_ms"] for p in body["points"]] == [250.0]


async def test_latency_defaults_to_24h(client, seed):
    m = await seed.monitor("a")
    await seed.commit()
    assert (await client.get(f"/monitors/{m.id}/latency")).json()["range"] == "24h"


async def test_latency_unknown_monitor_is_404(client):
    response = await client.get("/monitors/999/latency")
    assert response.status_code == 404 and response.json() == {"detail": "Monitor not found"}


async def test_latency_rejects_bad_range(client, seed):
    m = await seed.monitor("a")
    await seed.commit()
    assert (await client.get(f"/monitors/{m.id}/latency?range=1y")).status_code == 422


async def test_recent_checks_newest_first_and_limited(client, seed):
    m = await seed.monitor("gh")
    for i in range(15):
        seed.check(m, ago=(i + 1) * M, latency=100 + i)
    seed.check(m, ago=30 * M, ok=False)
    await seed.commit()
    rows = (await client.get("/checks/recent")).json()
    assert len(rows) == 12  # default limit
    assert [r["latency_ms"] for r in rows[:3]] == [100, 101, 102]
    assert rows[0]["short_code"] == "gh"
    assert len((await client.get("/checks/recent?limit=3")).json()) == 3


async def test_recent_checks_report_timeout_error(client, seed):
    m = await seed.monitor("api")
    seed.check(m, ago=M, ok=False)
    await seed.commit()
    [row] = (await client.get("/checks/recent")).json()
    assert (row["status_code"], row["ok"], row["error"]) == (None, False, "timeout")


@pytest.mark.parametrize("limit", [0, 101, "abc"])
async def test_recent_checks_validates_limit(client, limit):
    assert (await client.get(f"/checks/recent?limit={limit}")).status_code == 422


async def test_incidents_include_timeline_fields(client, seed):
    m = await seed.monitor("a")
    seed.check(m, ago=40 * M, ok=True)
    seed.check(m, ago=30 * M, ok=False)
    seed.check(m, ago=25 * M, ok=False)
    seed.incident(m, start_ago=30 * M, end_ago=None, cause="HTTP 500")
    await seed.commit()
    [incident] = (await client.get("/incidents")).json()
    assert incident["monitor_name"] == "A" and incident["cause"] == "HTTP 500"
    assert incident["resolved_at"] is None
    assert incident["last_ok_at"].startswith("2026-10-26T11:20")
    assert incident["started_at"].startswith("2026-10-26T11:30")
    assert incident["opened_at"].startswith("2026-10-26T11:35")


async def test_achievements_endpoint_lists_five(client, seed):
    await seed.monitor("a")
    await seed.commit()
    body = (await client.get("/achievements")).json()
    assert [a["id"] for a in body] == ["99_9_club", "sub_100ms", "iron_wall", "on_fire", "perfect_month"]
    assert set(body[0]) == {"id", "title", "description", "unlocked", "unlocked_at", "progress"}


# --- Cron endpoint -------------------------------------------------------------------------


@pytest.fixture
def fake_network(monkeypatch):
    from app import sweep

    real_make_client = sweep.make_client
    monkeypatch.setattr(settings, "cron_secret", "s3cret")
    monkeypatch.setattr(
        sweep, "make_client", lambda: real_make_client(httpx.MockTransport(lambda r: httpx.Response(200)))
    )


async def test_run_sweep_requires_secret(client, fake_network):
    assert (await client.post("/internal/run-sweep")).status_code == 401


async def test_run_sweep_rejects_wrong_secret(client, fake_network):
    response = await client.post("/internal/run-sweep", headers={"X-Cron-Secret": "nope"})
    assert response.status_code == 401


async def test_run_sweep_with_secret_runs_checks(client, seed, fake_network):
    await seed.monitor("a")
    await seed.commit()
    response = await client.post("/internal/run-sweep", headers={"X-Cron-Secret": "s3cret"})
    assert response.status_code == 200
    body = response.json()
    assert (body["sweep_id"], body["skipped"]) == (seed.sweep_id + 1, None)
    assert isinstance(body["duration_ms"], int) and body["duration_ms"] >= 0
    assert (await client.get("/checks/recent")).json()[0]["short_code"] == "a"


async def test_run_sweep_fails_closed_without_configured_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "")
    response = await client.post("/internal/run-sweep", headers={"X-Cron-Secret": ""})
    assert response.status_code == 503


async def test_run_sweep_skips_when_previous_sweep_is_too_recent(client, session, seed, fake_network):
    await seed.monitor("a")
    session.add(Sweep(started_at=NOW - timedelta(seconds=30)))
    await seed.commit()
    response = await client.post("/internal/run-sweep", headers={"X-Cron-Secret": "s3cret"})
    assert response.status_code == 200
    assert response.json() == {
        "sweep_id": None,
        "skipped": "last sweep was under 2 minutes ago, try again in 90s",
        "duration_ms": None,
    }
    assert (await client.get("/checks/recent")).json() == []


async def test_run_sweep_skips_while_another_sweep_holds_the_lock(client, session_factory, seed, fake_network):
    from app.sweep import SWEEP_LOCK_KEY

    await seed.monitor("a")
    await seed.commit()
    async with session_factory() as other:  # simulates a sweep already running
        await other.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": SWEEP_LOCK_KEY})
        response = await client.post("/internal/run-sweep", headers={"X-Cron-Secret": "s3cret"})
        await other.rollback()
    assert response.json() == {"sweep_id": None, "skipped": "another sweep is in progress", "duration_ms": None}


# --- Public "sweep now" button ------------------------------------------------------------


async def test_public_sweep_runs_without_a_secret(client, seed, fake_network):
    await seed.monitor("a")
    await seed.commit()
    response = await client.post("/sweep")
    assert response.status_code == 200 and response.json()["sweep_id"] == seed.sweep_id + 1


async def test_public_sweep_obeys_the_two_minute_gap(client, session, seed, fake_network):
    await seed.monitor("a")
    session.add(Sweep(started_at=NOW - timedelta(seconds=100)))
    await seed.commit()
    body = (await client.post("/sweep")).json()
    assert body["sweep_id"] is None and body["skipped"].endswith("try again in 20s")


async def test_summary_reports_how_long_the_last_sweep_took(client, session, seed):
    await seed.monitor("a")
    session.add(Sweep(started_at=NOW - timedelta(minutes=1, seconds=4), finished_at=NOW - timedelta(minutes=1)))
    await seed.commit()
    assert (await client.get("/summary")).json()["latest_sweep_duration_ms"] == 4000


async def test_cors_allows_post_from_the_frontend(client):
    response = await client.options(
        "/sweep", headers={"Origin": settings.cors_origin, "Access-Control-Request-Method": "POST"}
    )
    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]


# --- CORS and error mapping ----------------------------------------------------------------


async def test_cors_allows_only_configured_origin(client):
    ok = await client.get("/health", headers={"Origin": settings.cors_origin})
    bad = await client.get("/health", headers={"Origin": "https://evil.example"})
    assert ok.headers["access-control-allow-origin"] == settings.cors_origin
    assert "access-control-allow-origin" not in bad.headers


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (OperationalError("SELECT 1", {}, Exception("down")), 503),
        (ConnectionRefusedError("refused"), 503),
        (TimeoutError("slow"), 504),
        (ProgrammingError("SELECT 1", {}, Exception("bad")), 502),
        (RuntimeError("boom"), 500),
    ],
)
async def test_errors_map_to_http_status(client, error, status):
    async def broken_session():
        raise error
        yield  # pragma: no cover

    app.dependency_overrides[get_session] = broken_session
    response = await client.get("/monitors")
    assert response.status_code == status
    assert set(response.json()) == {"detail"}
