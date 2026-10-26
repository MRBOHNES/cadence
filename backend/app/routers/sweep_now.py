from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import get_now
from app.db import get_session
from app.schemas import SweepResult
from app.sweep import try_sweep

router = APIRouter(tags=["sweeps"])


@router.post("/sweep", response_model=SweepResult)
async def sweep_now(session: AsyncSession = Depends(get_session), now: datetime = Depends(get_now)) -> dict:
    """The page's "sweep now" button. Public, so no secret: the lock and the 2-minute gap in
    try_sweep cap it at one sweep every 2 minutes no matter who calls it."""
    return await try_sweep(session, now)
