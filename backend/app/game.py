"""Game layer: streaks, HP, rank and achievements. Everything derives from real checks/incidents."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import queries
from app.models import Achievement

DAY_SECONDS = 86400


def hp_for(uptime_30d: float | None) -> int:
    """0-10 blocks: 99.0% -> 0, 100% -> 10, one block per 0.1 percentage point.

    Half-up rounding on purpose: Python's round() is banker's rounding (9.5 -> 10 but 8.5 -> 8).
    """
    if uptime_30d is None:
        return 0
    return max(0, min(10, math.floor((uptime_30d - 99.0) / 0.1 + 0.5)))


def streaks(
    incidents: list[tuple[datetime, datetime | None]], since: datetime, now: datetime
) -> tuple[int, int]:
    """(current, best) streak in whole days between incidents.

    An incident is (started_at, resolved_at or None if still open). Overlapping incidents are
    merged; the best streak is the longest incident-free gap since `since`, including today's.
    """
    cursor, best_gap = since, 0.0
    for start, end in sorted(incidents, key=lambda i: i[0]):
        best_gap = max(best_gap, (start - cursor).total_seconds())
        cursor = max(cursor, end or now)
    current = 0.0 if any(end is None for _, end in incidents) else (now - cursor).total_seconds()
    best = max(best_gap, current)
    return int(current // DAY_SECONDS), int(best // DAY_SECONDS)


SINCE_SQL = text("""
    SELECT m.id, LEAST(m.created_at, COALESCE(min(c.checked_at), m.created_at)) AS since
    FROM monitors m LEFT JOIN checks c ON c.monitor_id = m.id GROUP BY m.id
""")
INCIDENT_SPANS_SQL = text("SELECT monitor_id, started_at, resolved_at FROM incidents")


async def streak_inputs(session: AsyncSession):
    since = {r.id: r.since for r in (await session.execute(SINCE_SQL)).all()}
    spans: dict[int, list[tuple[datetime, datetime | None]]] = {}
    for r in (await session.execute(INCIDENT_SPANS_SQL)).all():
        spans.setdefault(r.monitor_id, []).append((r.started_at, r.resolved_at))
    return since, spans


async def overall_streaks(session: AsyncSession, now: datetime) -> tuple[int, int]:
    since, spans = await streak_inputs(session)
    if not since:
        return 0, 0
    all_spans = [s for monitor_spans in spans.values() for s in monitor_spans]
    return streaks(all_spans, min(since.values()), now)


def rank_monitors(rows: list[dict]) -> None:
    """Add `rank` in place: 30d uptime desc, then median latency asc (missing data sorts last)."""
    ordered = sorted(
        rows,
        key=lambda r: (
            -(r["uptime_30d"] if r["uptime_30d"] is not None else -1),
            r["p50_ms"] if r["p50_ms"] is not None else math.inf,
        ),
    )
    for position, row in enumerate(ordered, start=1):
        row["rank"] = position


async def enrich_monitors(session: AsyncSession, rows: list[dict], now: datetime) -> list[dict]:
    since, spans = await streak_inputs(session)
    for row in rows:
        row["hp"] = hp_for(row["uptime_30d"])
        row["streak_days"] = streaks(spans.get(row["id"], []), since[row["id"]], now)[0]
    rank_monitors(rows)
    return rows


# --- Achievements -------------------------------------------------------------------------

HISTORY_SQL = text("""
    SELECT COALESCE(EXTRACT(EPOCH FROM (CAST(:now AS timestamptz) - min(checked_at))) / 86400, 0) AS days,
           count(*) FILTER (WHERE status_code >= 500
             AND checked_at > CAST(:now AS timestamptz) - interval '7 days') AS server_errors_7d
    FROM checks
""")


@dataclass
class Facts:
    monitors: list[dict]
    history_days: float
    server_errors_7d: int
    streak_days: int


@dataclass
class Rule:
    id: str
    title: str
    description: str
    evaluate: Callable[[Facts], tuple[bool, str]]  # -> (unlocked, progress text)


def _needs_history(facts: Facts, days: int) -> str | None:
    if facts.history_days < days:
        return f"COLLECTING DATA · {int(facts.history_days)} / {days} DAYS"
    return None


def _club_999(f: Facts) -> tuple[bool, str]:
    total = len(f.monitors)
    needed = min(3, total)
    above = sum((m["uptime_30d"] or 0) >= 99.9 for m in f.monitors)
    waiting = _needs_history(f, 30)
    return (total > 0 and above >= needed and waiting is None), waiting or f"{above} / {needed} SERVICES"


def _sub_100(f: Facts) -> tuple[bool, str]:
    p50s = [m["p50_ms"] for m in f.monitors if m["p50_ms"] is not None]
    if not p50s:
        return False, "NO DATA YET"
    return min(p50s) < 100, f"BEST P50 {round(min(p50s))} MS"


def _iron_wall(f: Facts) -> tuple[bool, str]:
    waiting = _needs_history(f, 7)
    if waiting:
        return False, waiting
    return f.server_errors_7d == 0, f"{f.server_errors_7d} SERVER ERRORS IN 7D"


def _on_fire(f: Facts) -> tuple[bool, str]:
    return f.streak_days >= 30, f"{f.streak_days} / 30 DAYS"


def _perfect_month(f: Facts) -> tuple[bool, str]:
    total = len(f.monitors)
    perfect = sum(m["uptime_30d"] == 100.0 for m in f.monitors)
    waiting = _needs_history(f, 30)
    return (total > 0 and perfect == total and waiting is None), waiting or f"{perfect} / {total} SERVICES"


RULES = [
    Rule("99_9_club", "99.9 CLUB", "3 services above 99.9% uptime over 30 days", _club_999),
    Rule("sub_100ms", "SUB-100MS", "Any service with a median under 100 ms over 24 hours", _sub_100),
    Rule("iron_wall", "IRON WALL", "No 5xx responses in 7 days", _iron_wall),
    Rule("on_fire", "ON FIRE", "30 days without an incident", _on_fire),
    Rule("perfect_month", "PERFECT MONTH", "Every service at 100% for 30 days", _perfect_month),
]


async def achievements(session: AsyncSession, now: datetime) -> list[dict]:
    monitors = await enrich_monitors(session, await queries.monitor_rows(session, now), now)
    history = (await session.execute(HISTORY_SQL, {"now": now})).one()
    streak_days, _ = await overall_streaks(session, now)
    facts = Facts(monitors, float(history.days), history.server_errors_7d, streak_days)

    results = {rule.id: rule.evaluate(facts) for rule in RULES}
    # Record first unlock time; ON CONFLICT DO NOTHING keeps the original timestamp.
    newly = [{"id": rid, "unlocked_at": now} for rid, (ok, _) in results.items() if ok]
    if newly:
        await session.execute(insert(Achievement).values(newly).on_conflict_do_nothing())
        await session.commit()
    unlocked_at = {a.id: a.unlocked_at for a in (await session.scalars(select(Achievement))).all()}

    return [
        {
            "id": rule.id,
            "title": rule.title,
            "description": rule.description,
            "unlocked": results[rule.id][0],
            "unlocked_at": unlocked_at.get(rule.id) if results[rule.id][0] else None,
            "progress": None if results[rule.id][0] else results[rule.id][1],
        }
        for rule in RULES
    ]
