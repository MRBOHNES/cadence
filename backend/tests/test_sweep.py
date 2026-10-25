import asyncio
import time

import httpx
import pytest
from sqlalchemy import select

from app.models import Check, Incident
from app.sweep import check_url, make_client, run_sweep


def client_for(behaviour: dict) -> httpx.AsyncClient:
    """Fake network: behaviour maps host -> status code, or an exception to raise."""

    def handler(request: httpx.Request) -> httpx.Response:
        outcome = behaviour[request.url.host]
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome)

    return make_client(httpx.MockTransport(handler))


# --- check_url: classification -------------------------------------------------------------


@pytest.mark.parametrize("status", [200, 204, 301, 404])
async def test_non_5xx_counts_as_up(status):
    async with client_for({"a.example": status}) as c:
        result = await check_url(c, "https://a.example")
    assert result.ok and result.error is None
    assert result.status_code == status and result.latency_ms is not None


@pytest.mark.parametrize("status", [500, 502, 503])
async def test_5xx_counts_as_down(status):
    async with client_for({"a.example": status}) as c:
        result = await check_url(c, "https://a.example")
    assert not result.ok
    assert result.status_code == status
    assert result.error == f"HTTP {status}"


async def test_timeout_is_down_without_status_or_latency():
    async with client_for({"a.example": httpx.ReadTimeout("slow")}) as c:
        result = await check_url(c, "https://a.example")
    assert (result.ok, result.status_code, result.latency_ms, result.error) == (False, None, None, "timeout")


async def test_connection_error_is_down():
    async with client_for({"a.example": httpx.ConnectError("refused")}) as c:
        result = await check_url(c, "https://a.example")
    assert not result.ok and result.status_code is None
    assert result.error == "connection error: ConnectError"


def test_client_uses_ten_second_timeout():
    assert make_client().timeout == httpx.Timeout(10.0)


# --- run_sweep -----------------------------------------------------------------------------


async def test_sweep_records_one_check_per_monitor(session, seed):
    await seed.monitor("a")
    await seed.monitor("b")
    await seed.commit()
    async with client_for({"a.example": 200, "b.example": 503}) as c:
        sweep = await run_sweep(session, c)
    checks = (await session.scalars(select(Check).where(Check.sweep_id == sweep.id))).all()
    assert sorted((c.monitor_id, c.ok) for c in checks) == [(1, True), (2, False)]
    assert sweep.finished_at is not None and sweep.finished_at >= sweep.started_at


async def test_sweep_checks_run_in_parallel(session, seed):
    for code in "abcd":
        await seed.monitor(code)
    await seed.commit()

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.3)
        return httpx.Response(200)

    async with make_client(httpx.MockTransport(slow_handler)) as c:
        started = time.perf_counter()
        await run_sweep(session, c)
    assert time.perf_counter() - started < 0.9  # sequential would be >= 1.2s


async def test_one_slow_monitor_failing_does_not_break_others(session, seed):
    await seed.monitor("a")
    await seed.monitor("b")
    await seed.commit()
    async with client_for({"a.example": httpx.ReadTimeout("x"), "b.example": 200}) as c:
        await run_sweep(session, c)
    oks = {c.monitor_id: c.ok for c in (await session.scalars(select(Check))).all()}
    assert oks == {1: False, 2: True}


# --- Incident rules ------------------------------------------------------------------------


async def sweeps(session, behaviour: dict, n: int = 1):
    async with client_for(behaviour) as c:
        for _ in range(n):
            await run_sweep(session, c)


async def incidents(session) -> list[Incident]:
    return list((await session.scalars(select(Incident).order_by(Incident.id))).all())


@pytest.fixture
async def one_monitor(session, seed):
    await seed.monitor("a")
    await seed.commit()


async def test_single_failure_opens_no_incident(session, one_monitor):
    await sweeps(session, {"a.example": 500})
    assert await incidents(session) == []


async def test_two_consecutive_failures_open_incident(session, one_monitor):
    await sweeps(session, {"a.example": 500}, n=2)
    [incident] = await incidents(session)
    assert incident.resolved_at is None and incident.cause == "HTTP 500"


async def test_incident_starts_at_first_failure(session, one_monitor):
    await sweeps(session, {"a.example": 500}, n=2)
    first = (await session.scalars(select(Check).order_by(Check.checked_at))).first()
    [incident] = await incidents(session)
    assert incident.started_at == first.checked_at


async def test_third_failure_does_not_open_second_incident(session, one_monitor):
    await sweeps(session, {"a.example": httpx.ReadTimeout("x")}, n=4)
    assert len(await incidents(session)) == 1


async def test_success_resolves_open_incident(session, one_monitor):
    await sweeps(session, {"a.example": 500}, n=2)
    await sweeps(session, {"a.example": 200})
    [incident] = await incidents(session)
    assert incident.resolved_at is not None


async def test_failure_success_failure_does_not_open_incident(session, one_monitor):
    await sweeps(session, {"a.example": 500})
    await sweeps(session, {"a.example": 200})
    await sweeps(session, {"a.example": 500})
    assert await incidents(session) == []


async def test_new_incident_after_recovery(session, one_monitor):
    await sweeps(session, {"a.example": 500}, n=2)
    await sweeps(session, {"a.example": 200})
    await sweeps(session, {"a.example": 500}, n=2)
    resolved = [i.resolved_at is not None for i in await incidents(session)]
    assert resolved == [True, False]


async def test_incidents_are_tracked_per_monitor(session, seed):
    await seed.monitor("a")
    await seed.monitor("b")
    await seed.commit()
    await sweeps(session, {"a.example": 500, "b.example": 200}, n=2)
    [incident] = await incidents(session)
    assert incident.monitor_id == 1
