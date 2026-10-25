"""Upsert the monitors in seed/monitors.json. Safe to run repeatedly.

Usage: uv run python -m scripts.seed
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Monitor

SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "monitors.json"


async def seed() -> int:
    entries = json.loads(SEED_FILE.read_text())
    async with SessionLocal() as session:
        existing = {m.short_code: m for m in (await session.scalars(select(Monitor))).all()}
        for entry in entries:
            monitor = existing.get(entry["short_code"])
            if monitor:
                monitor.name, monitor.url = entry["name"], entry["url"]
            else:
                session.add(Monitor(**entry))
        await session.commit()
    await engine.dispose()
    return len(entries)


if __name__ == "__main__":
    print(f"Seeded {asyncio.run(seed())} monitors")
