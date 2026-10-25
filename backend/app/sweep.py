"""The sweep: check every monitor in parallel, store results, update incidents."""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Check, Incident, Monitor, Sweep

CHECK_TIMEOUT_SECONDS = 10.0
FAILURES_TO_OPEN_INCIDENT = 2


@dataclass
class CheckResult:
    status_code: int | None
    latency_ms: int | None
    ok: bool
    error: str | None


def make_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=CHECK_TIMEOUT_SECONDS, follow_redirects=True, transport=transport
    )


async def check_url(client: httpx.AsyncClient, url: str) -> CheckResult:
    """One HTTP GET. Down = timeout, connection error or 5xx. Never raises."""
    start = time.perf_counter()
    try:
        response = await client.get(url)
    except httpx.TimeoutException:
        return CheckResult(None, None, False, "timeout")
    except httpx.HTTPError as exc:
        return CheckResult(None, None, False, f"connection error: {type(exc).__name__}")
    latency_ms = round((time.perf_counter() - start) * 1000)
    if response.status_code >= 500:
        return CheckResult(response.status_code, latency_ms, False, f"HTTP {response.status_code}")
    return CheckResult(response.status_code, latency_ms, True, None)


async def update_incident(
    session: AsyncSession, monitor_id: int, sweep_id: int, check: Check
) -> None:
    """Open an incident after 2 consecutive failures; resolve it on the next success."""
    open_incident = await session.scalar(
        select(Incident).where(Incident.monitor_id == monitor_id, Incident.resolved_at.is_(None))
    )
    if check.ok:
        if open_incident:
            open_incident.resolved_at = check.checked_at
        return
    if open_incident:
        return
    # Last FAILURES_TO_OPEN_INCIDENT - 1 checks before this one (this sweep excluded).
    previous = (
        await session.scalars(
            select(Check)
            .where(Check.monitor_id == monitor_id, Check.sweep_id != sweep_id)
            .order_by(Check.checked_at.desc())
            .limit(FAILURES_TO_OPEN_INCIDENT - 1)
        )
    ).all()
    if len(previous) == FAILURES_TO_OPEN_INCIDENT - 1 and all(not c.ok for c in previous):
        first_failure = previous[-1]
        session.add(
            Incident(
                monitor_id=monitor_id,
                started_at=first_failure.checked_at,
                cause=check.error or "check failed",
            )
        )


async def run_sweep(session: AsyncSession, client: httpx.AsyncClient) -> Sweep:
    now = datetime.now(UTC)
    sweep = Sweep(started_at=now)
    session.add(sweep)
    await session.flush()  # assigns sweep.id

    monitors = (await session.scalars(select(Monitor).order_by(Monitor.id))).all()
    results = await asyncio.gather(*(check_url(client, m.url) for m in monitors))

    for monitor, result in zip(monitors, results, strict=True):
        check = Check(
            sweep_id=sweep.id,
            monitor_id=monitor.id,
            checked_at=datetime.now(UTC),
            status_code=result.status_code,
            latency_ms=result.latency_ms,
            ok=result.ok,
            error=result.error,
        )
        session.add(check)
        await session.flush()
        await update_incident(session, monitor.id, sweep.id, check)

    sweep.finished_at = datetime.now(UTC)
    await session.commit()
    return sweep
