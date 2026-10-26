"""The sweep: check every monitor in parallel, store results, update incidents."""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Check, Incident, Monitor, Sweep

CHECK_TIMEOUT_SECONDS = 10.0
FAILURES_TO_OPEN_INCIDENT = 2
# Two sweeps closer than this would count one outage twice and defeat the 2-failure rule.
# It also absorbs the cron's retry, and rate-limits the public "sweep now" button.
MIN_SWEEP_GAP = timedelta(minutes=2)
# Arbitrary app-wide key for Postgres advisory locks: "one sweep at a time".
SWEEP_LOCK_KEY = 7_202_604


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


def duration_ms(sweep: Sweep) -> int | None:
    if sweep.finished_at is None:
        return None
    return round((sweep.finished_at - sweep.started_at).total_seconds() * 1000)


async def try_sweep(session: AsyncSession, now: datetime) -> dict:
    """Run a sweep unless one is in progress or the last one started under MIN_SWEEP_GAP ago.

    Both the cron endpoint and the public button go through here, so the rules are the same.
    """
    # Transaction-scoped lock: released automatically when run_sweep commits or we roll back.
    locked = await session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SWEEP_LOCK_KEY})
    if not locked:
        return {"sweep_id": None, "skipped": "another sweep is in progress", "duration_ms": None}

    last_started = await session.scalar(select(func.max(Sweep.started_at)))
    if last_started is not None and now - last_started < MIN_SWEEP_GAP:
        await session.rollback()  # releases the lock
        wait = int((MIN_SWEEP_GAP - (now - last_started)).total_seconds())
        return {"sweep_id": None, "skipped": f"last sweep was under 2 minutes ago, try again in {wait}s", "duration_ms": None}

    async with make_client() as client:
        sweep = await run_sweep(session, client)
    return {"sweep_id": sweep.id, "skipped": None, "duration_ms": duration_ms(sweep)}
