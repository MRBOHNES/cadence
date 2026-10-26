import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import get_now
from app.config import settings
from app.db import get_session
from app.models import Sweep
from app.schemas import SweepResult
from app.sweep import make_client, run_sweep

router = APIRouter(prefix="/internal", tags=["internal"])

# Two sweeps closer than this would count one outage twice and defeat the 2-failure rule.
# It also absorbs the cron's retry when the first request did finish on the server.
MIN_SWEEP_GAP = timedelta(minutes=2)
# Arbitrary app-wide key for Postgres advisory locks: "one sweep at a time".
SWEEP_LOCK_KEY = 7_202_604


def require_cron_secret(x_cron_secret: str = Header(default="")) -> None:
    if not settings.cron_secret:
        # Fail closed: an unset secret must never mean "no secret needed".
        raise HTTPException(status_code=503, detail="Sweeps are disabled: CRON_SECRET is not set")
    # compare_digest avoids leaking the secret through response timing.
    if not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.post("/run-sweep", response_model=SweepResult, dependencies=[Depends(require_cron_secret)])
async def run_sweep_endpoint(
    session: AsyncSession = Depends(get_session), now: datetime = Depends(get_now)
) -> dict:
    # Transaction-scoped lock: released automatically when run_sweep commits.
    locked = await session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SWEEP_LOCK_KEY})
    if not locked:
        return {"sweep_id": None, "skipped": "another sweep is in progress"}

    last_started = await session.scalar(select(func.max(Sweep.started_at)))
    if last_started is not None and now - last_started < MIN_SWEEP_GAP:
        await session.rollback()  # releases the lock
        seconds = int((now - last_started).total_seconds())
        return {"sweep_id": None, "skipped": f"previous sweep started {seconds}s ago"}

    async with make_client() as client:
        sweep = await run_sweep(session, client)
    return {"sweep_id": sweep.id, "skipped": None}
