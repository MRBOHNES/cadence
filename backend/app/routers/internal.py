import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.sweep import make_client, run_sweep

router = APIRouter(prefix="/internal", tags=["internal"])


def require_cron_secret(x_cron_secret: str = Header(default="")) -> None:
    # compare_digest avoids leaking the secret through response timing.
    if not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.post("/run-sweep", dependencies=[Depends(require_cron_secret)])
async def run_sweep_endpoint(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    async with make_client() as client:
        sweep = await run_sweep(session, client)
    return {"sweep_id": sweep.id}
