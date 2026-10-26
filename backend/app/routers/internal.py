import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import get_now
from app.config import settings
from app.db import get_session
from app.schemas import SweepResult
from app.sweep import try_sweep

router = APIRouter(prefix="/internal", tags=["internal"])


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
    return await try_sweep(session, now)
