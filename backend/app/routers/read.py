from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import game, queries
from app.db import get_session
from app.models import Monitor
from app.schemas import (
    AchievementOut,
    IncidentOut,
    LatencyRange,
    LatencySeries,
    MonitorOut,
    RecentCheck,
    Summary,
)

router = APIRouter()
SWEEP_INTERVAL = timedelta(minutes=5)


def get_now() -> datetime:
    """Injected so tests can pin the clock."""
    return datetime.now(UTC)


@router.get("/summary", response_model=Summary)
async def summary(
    session: AsyncSession = Depends(get_session), now: datetime = Depends(get_now)
) -> dict:
    row = await queries.summary_row(session, now)
    monitors = await queries.monitor_rows(session, now)
    started = row.pop("sweep_started_at")
    streak, best = await game.overall_streaks(session, now)
    return {
        **row,
        "streak_days": streak,
        "best_streak_days": best,
        "services_up": sum(m["state"] in ("up", "slow") for m in monitors),
        "services_total": len(monitors),
        "next_sweep_at": started + SWEEP_INTERVAL if started else None,
    }


@router.get("/monitors", response_model=list[MonitorOut])
async def monitors(
    session: AsyncSession = Depends(get_session), now: datetime = Depends(get_now)
) -> list[dict]:
    return await game.enrich_monitors(session, await queries.monitor_rows(session, now), now)


@router.get("/monitors/{monitor_id}/latency", response_model=LatencySeries)
async def monitor_latency(
    monitor_id: int,
    range: LatencyRange = "24h",
    session: AsyncSession = Depends(get_session),
    now: datetime = Depends(get_now),
) -> dict:
    if await session.scalar(select(Monitor.id).where(Monitor.id == monitor_id)) is None:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return await queries.latency_series(session, monitor_id, range, now)


@router.get("/checks/recent", response_model=list[RecentCheck])
async def recent_checks(
    limit: int = Query(12, ge=1, le=100), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    return await queries.recent_checks(session, limit)


@router.get("/incidents", response_model=list[IncidentOut])
async def incidents(
    limit: int = Query(20, ge=1, le=100), session: AsyncSession = Depends(get_session)
) -> list[dict]:
    return await queries.incidents(session, limit)


@router.get("/achievements", response_model=list[AchievementOut])
async def achievements(
    session: AsyncSession = Depends(get_session), now: datetime = Depends(get_now)
) -> list[dict]:
    return await game.achievements(session, now)
