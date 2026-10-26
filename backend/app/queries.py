"""All read-side SQL. Aggregates (uptime, percentiles, daily buckets) live in the database."""

from datetime import datetime

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

SLOW_MS = 500
LATENCY_BINS = {"24h": ("24 hours", "5 minutes"), "7d": ("7 days", "1 hour"), "30d": ("30 days", "6 hours")}


def q(sql: str) -> TextClause:
    """Wrap SQL whose :now parameter is a timestamptz (explicit type keeps asyncpg happy)."""
    return text(sql).bindparams(bindparam("now", type_=DateTime(timezone=True)))


def _round(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(float(value), digits)


MONITOR_STATS_SQL = q("""
    SELECT m.id, m.name, m.short_code, m.url,
      ROUND(100.0 * count(c.id) FILTER (WHERE c.ok AND c.checked_at > :now - interval '24 hours')
        / NULLIF(count(c.id) FILTER (WHERE c.checked_at > :now - interval '24 hours'), 0), 3) AS uptime_24h,
      ROUND(100.0 * count(c.id) FILTER (WHERE c.ok) / NULLIF(count(c.id), 0), 3) AS uptime_30d,
      percentile_cont(0.5) WITHIN GROUP (ORDER BY c.latency_ms)
        FILTER (WHERE c.checked_at > :now - interval '24 hours') AS p50_ms,
      percentile_cont(0.95) WITHIN GROUP (ORDER BY c.latency_ms)
        FILTER (WHERE c.checked_at > :now - interval '24 hours') AS p95_ms
    FROM monitors m
    LEFT JOIN checks c ON c.monitor_id = m.id
      AND c.checked_at > :now - interval '30 days' AND c.checked_at <= :now
    GROUP BY m.id ORDER BY m.id
""")

# Latest check per monitor decides the current state.
LATEST_CHECK_SQL = text("""
    SELECT DISTINCT ON (monitor_id) monitor_id, ok, latency_ms
    FROM checks ORDER BY monitor_id, checked_at DESC
""")

# One row per (monitor, IST calendar day) for the last 30 days. Days with no checks still
# appear thanks to the generate_series cross join.
DAILY_BUCKETS_SQL = q("""
    WITH days AS (
      SELECT generate_series(
        date_trunc('day', :now AT TIME ZONE 'Asia/Kolkata') - interval '29 days',
        date_trunc('day', :now AT TIME ZONE 'Asia/Kolkata'),
        interval '1 day') AS day
    )
    SELECT m.id AS monitor_id, d.day,
      count(c.id) AS total,
      count(c.id) FILTER (WHERE NOT c.ok) AS failed,
      count(c.id) FILTER (WHERE c.ok AND c.latency_ms > :slow_ms) AS slow
    FROM monitors m
    CROSS JOIN days d
    LEFT JOIN checks c ON c.monitor_id = m.id
      AND c.checked_at >= (d.day AT TIME ZONE 'Asia/Kolkata')
      AND c.checked_at < ((d.day + interval '1 day') AT TIME ZONE 'Asia/Kolkata')
      AND c.checked_at <= :now
    GROUP BY m.id, d.day ORDER BY m.id, d.day
""")


def day_status(total: int, failed: int, slow: int) -> str:
    """No data / down (<95% up that day) / degraded (any failure, or mostly slow) / up."""
    if total == 0:
        return "no-data"
    if (total - failed) / total < 0.95:
        return "down"
    if failed > 0 or slow * 2 >= total:
        return "degraded"
    return "up"


async def monitor_rows(session: AsyncSession, now: datetime) -> list[dict]:
    rows = (await session.execute(MONITOR_STATS_SQL, {"now": now})).mappings().all()
    latest = {r.monitor_id: r for r in (await session.execute(LATEST_CHECK_SQL)).all()}
    buckets = (await session.execute(DAILY_BUCKETS_SQL, {"now": now, "slow_ms": SLOW_MS})).mappings().all()
    history: dict[int, list[str]] = {}
    for b in buckets:
        history.setdefault(b["monitor_id"], []).append(day_status(b["total"], b["failed"], b["slow"]))

    out = []
    for r in rows:
        last = latest.get(r["id"])
        if last is None:
            state = "unknown"
        elif not last.ok:
            state = "down"
        elif last.latency_ms is not None and last.latency_ms > SLOW_MS:
            state = "slow"
        else:
            state = "up"
        out.append(
            {
                "id": r["id"],
                "name": r["name"],
                "short_code": r["short_code"],
                "url": r["url"],
                "state": state,
                "uptime_24h": _round(r["uptime_24h"]),
                "uptime_30d": _round(r["uptime_30d"]),
                "p50_ms": _round(r["p50_ms"], 1),
                "p95_ms": _round(r["p95_ms"], 1),
                "history": history.get(r["id"], ["no-data"] * 30),
            }
        )
    return out


SUMMARY_SQL = q("""
    SELECT
      ROUND(100.0 * count(*) FILTER (WHERE ok AND checked_at > :now - interval '30 days')
        / NULLIF(count(*) FILTER (WHERE checked_at > :now - interval '30 days'), 0), 3) AS uptime_cur,
      ROUND(100.0 * count(*) FILTER (WHERE ok AND checked_at <= :now - interval '30 days')
        / NULLIF(count(*) FILTER (WHERE checked_at <= :now - interval '30 days'), 0), 3) AS uptime_prev,
      percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms)
        FILTER (WHERE checked_at > :now - interval '24 hours') AS p50_cur,
      percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
        FILTER (WHERE checked_at > :now - interval '24 hours') AS p95_cur,
      count(*) FILTER (WHERE checked_at > :now - interval '24 hours') AS checks_24h,
      count(*) FILTER (WHERE NOT ok AND checked_at > :now - interval '24 hours') AS failed_24h
    FROM checks
    WHERE checked_at > :now - interval '60 days' AND checked_at <= :now
""")
PREV_LATENCY_SQL = q("""
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
    FROM checks
    WHERE checked_at <= :now - interval '24 hours' AND checked_at > :now - interval '48 hours'
""")

SWEEP_SQL = text("""
    SELECT id AS latest, started_at AS started,
           ROUND(EXTRACT(EPOCH FROM (finished_at - started_at)) * 1000)::int AS duration_ms
    FROM sweeps ORDER BY id DESC LIMIT 1
""")
OPEN_INCIDENTS_SQL = text("SELECT count(*) FROM incidents WHERE resolved_at IS NULL")


def _delta(cur: float | None, prev: float | None, digits: int = 3) -> float | None:
    return None if cur is None or prev is None else round(float(cur) - float(prev), digits)


async def summary_row(session: AsyncSession, now: datetime) -> dict:
    s = (await session.execute(SUMMARY_SQL, {"now": now})).mappings().one()
    prev = (await session.execute(PREV_LATENCY_SQL, {"now": now})).mappings().one()
    sweep = (await session.execute(SWEEP_SQL)).mappings().one_or_none() or {}
    open_incidents = (await session.execute(OPEN_INCIDENTS_SQL)).scalar_one()
    return {
        "uptime_30d": _round(s["uptime_cur"]),
        "uptime_change": _delta(s["uptime_cur"], s["uptime_prev"]),
        "median_ms_24h": _round(s["p50_cur"], 1),
        "median_change_ms": _delta(s["p50_cur"], prev["p50"], 1),
        "p95_ms_24h": _round(s["p95_cur"], 1),
        "p95_change_ms": _delta(s["p95_cur"], prev["p95"], 1),
        "checks_24h": s["checks_24h"],
        "failed_24h": s["failed_24h"],
        "latest_sweep": sweep.get("latest"),
        "latest_sweep_duration_ms": sweep.get("duration_ms"),
        "sweep_started_at": sweep.get("started"),
        "open_incidents": open_incidents,
    }


async def latency_series(session: AsyncSession, monitor_id: int, range_: str, now: datetime) -> dict:
    window, step = LATENCY_BINS[range_]
    # date_bin snaps each check to a fixed-size time bucket; we chart the average per bucket.
    points_sql = q(f"""
        SELECT date_bin(interval '{step}', checked_at, TIMESTAMPTZ '2000-01-01') AS t,
               AVG(latency_ms)::float AS latency_ms
        FROM checks
        WHERE monitor_id = :monitor_id AND latency_ms IS NOT NULL
          AND checked_at > :now - interval '{window}' AND checked_at <= :now
        GROUP BY t ORDER BY t
    """)
    stats_sql = q(f"""
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
        FROM checks
        WHERE monitor_id = :monitor_id AND checked_at > :now - interval '{window}' AND checked_at <= :now
    """)
    params = {"monitor_id": monitor_id, "now": now}
    points = (await session.execute(points_sql, params)).mappings().all()
    stats = (await session.execute(stats_sql, params)).mappings().one()
    return {
        "monitor_id": monitor_id,
        "range": range_,
        "p50_ms": _round(stats["p50"], 1),
        "p95_ms": _round(stats["p95"], 1),
        "points": [{"t": p["t"], "latency_ms": round(p["latency_ms"], 1)} for p in points],
    }


RECENT_SQL = text("""
    SELECT c.id, c.checked_at, m.short_code, c.status_code, c.latency_ms, c.ok, c.error
    FROM checks c JOIN monitors m ON m.id = c.monitor_id
    ORDER BY c.checked_at DESC, c.id DESC LIMIT :limit
""")

# last_ok_at: latest good check before the incident. opened_at: the failed check that tripped
# the 2-failure rule, i.e. the second failure on or after started_at.
INCIDENTS_SQL = text("""
    SELECT i.id, i.monitor_id, m.name AS monitor_name, m.short_code, i.started_at, i.resolved_at, i.cause,
      (SELECT max(c.checked_at) FROM checks c
        WHERE c.monitor_id = i.monitor_id AND c.ok AND c.checked_at < i.started_at) AS last_ok_at,
      (SELECT c.checked_at FROM checks c
        WHERE c.monitor_id = i.monitor_id AND NOT c.ok AND c.checked_at >= i.started_at
        ORDER BY c.checked_at OFFSET 1 LIMIT 1) AS opened_at
    FROM incidents i JOIN monitors m ON m.id = i.monitor_id
    ORDER BY i.started_at DESC LIMIT :limit
""")


async def recent_checks(session: AsyncSession, limit: int) -> list[dict]:
    return [dict(r) for r in (await session.execute(RECENT_SQL, {"limit": limit})).mappings().all()]


async def incidents(session: AsyncSession, limit: int) -> list[dict]:
    return [dict(r) for r in (await session.execute(INCIDENTS_SQL, {"limit": limit})).mappings().all()]
