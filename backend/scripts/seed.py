"""Make the monitors table match seed/monitors.json. Safe to run repeatedly.

The file is the source of truth: monitors are matched by `short_code`, new ones are added,
existing ones are updated, and monitors no longer in the file are removed with their checks and
incidents.

Usage: uv run python -m scripts.seed
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.models import Check, Incident, Monitor

SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "monitors.json"


async def sync_monitors(session: AsyncSession, entries: list[dict]) -> list[str]:
    """Apply `entries` to the table and return the short codes that were removed."""
    existing = {m.short_code: m for m in (await session.scalars(select(Monitor))).all()}
    wanted = {e["short_code"] for e in entries}

    for entry in entries:
        monitor = existing.get(entry["short_code"])
        if monitor:
            monitor.name, monitor.url = entry["name"], entry["url"]
        else:
            session.add(Monitor(**entry))

    removed = [m for code, m in existing.items() if code not in wanted]
    if removed:
        ids = [m.id for m in removed]
        await session.execute(delete(Check).where(Check.monitor_id.in_(ids)))
        await session.execute(delete(Incident).where(Incident.monitor_id.in_(ids)))
        await session.execute(delete(Monitor).where(Monitor.id.in_(ids)))
    await session.commit()
    return sorted(m.short_code for m in removed)


async def seed() -> str:
    entries = json.loads(SEED_FILE.read_text())
    async with SessionLocal() as session:
        removed = await sync_monitors(session, entries)
    await engine.dispose()
    return f"Seeded {len(entries)} monitors" + (f", removed {', '.join(removed)}" if removed else "")


if __name__ == "__main__":
    print(asyncio.run(seed()))
