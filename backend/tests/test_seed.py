import json
from datetime import timedelta

from sqlalchemy import func, select

from app.models import Check, Incident, Monitor
from scripts.seed import SEED_FILE, sync_monitors


async def codes(session) -> list[str]:
    return sorted((await session.scalars(select(Monitor.short_code))).all())


async def test_adds_new_monitors(session):
    await sync_monitors(session, [{"name": "A", "short_code": "a", "url": "https://a.example"}])
    assert await codes(session) == ["a"]


async def test_updates_existing_monitor_in_place(session, seed):
    m = await seed.monitor("a")
    await seed.commit()
    await sync_monitors(session, [{"name": "Renamed", "short_code": "a", "url": "https://new.example"}])
    updated = await session.scalar(select(Monitor).where(Monitor.short_code == "a"))
    assert (updated.id, updated.name, updated.url) == (m.id, "Renamed", "https://new.example")


async def test_removes_monitors_missing_from_the_file_with_their_history(session, seed):
    keep, drop = await seed.monitor("kp"), await seed.monitor("old")
    seed.check(keep, ago=timedelta(minutes=5))
    seed.check(drop, ago=timedelta(minutes=5), ok=False)
    seed.incident(drop, start_ago=timedelta(minutes=10), end_ago=None)
    await seed.commit()

    removed = await sync_monitors(session, [{"name": "Keep", "short_code": "kp", "url": keep.url}])

    assert removed == ["old"]
    assert await codes(session) == ["kp"]
    assert await session.scalar(select(func.count()).select_from(Check)) == 1
    assert await session.scalar(select(func.count()).select_from(Incident)) == 0


def test_seed_file_is_valid():
    entries = json.loads(SEED_FILE.read_text())
    codes_in_file = [e["short_code"] for e in entries]
    assert 3 <= len(entries) <= 5
    assert len(set(codes_in_file)) == len(codes_in_file)
    assert all(2 <= len(c) <= 3 for c in codes_in_file)
    assert all(e["url"].startswith("https://") for e in entries)
