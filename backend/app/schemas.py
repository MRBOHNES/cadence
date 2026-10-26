from datetime import datetime
from typing import Literal

from pydantic import BaseModel

MonitorState = Literal["up", "slow", "down", "unknown"]
DayStatus = Literal["up", "degraded", "down", "no-data"]
LatencyRange = Literal["24h", "7d", "30d"]


class Summary(BaseModel):
    uptime_30d: float | None
    uptime_change: float | None  # percentage points vs the previous 30 days
    services_up: int
    services_total: int
    median_ms_24h: float | None
    median_change_ms: float | None  # vs the previous 24 hours
    p95_ms_24h: float | None
    p95_change_ms: float | None
    checks_24h: int
    failed_24h: int
    latest_sweep: int | None
    latest_sweep_at: datetime | None
    next_sweep_at: datetime | None
    streak_days: int  # days since the last incident, all services
    best_streak_days: int
    open_incidents: int


class MonitorOut(BaseModel):
    id: int
    name: str
    short_code: str
    url: str
    state: MonitorState
    uptime_24h: float | None
    uptime_30d: float | None
    p50_ms: float | None
    p95_ms: float | None
    history: list[DayStatus]  # 30 daily buckets, oldest first
    streak_days: int
    hp: int  # 0-10
    rank: int  # 1 = best 30d uptime, ties broken by lower median latency


class LatencyPoint(BaseModel):
    t: datetime
    latency_ms: float


class LatencySeries(BaseModel):
    monitor_id: int
    range: LatencyRange
    p50_ms: float | None
    p95_ms: float | None
    points: list[LatencyPoint]


class RecentCheck(BaseModel):
    id: int
    checked_at: datetime
    short_code: str
    status_code: int | None
    latency_ms: int | None
    ok: bool
    error: str | None


class IncidentOut(BaseModel):
    id: int
    monitor_id: int
    monitor_name: str
    short_code: str
    started_at: datetime  # first failed check
    resolved_at: datetime | None
    cause: str
    last_ok_at: datetime | None  # last good check before the failures
    opened_at: datetime | None  # the failure that tripped the 2-failure rule


class AchievementOut(BaseModel):
    id: str
    title: str
    description: str
    unlocked: bool
    unlocked_at: datetime | None
    progress: str | None  # shown while locked


class SweepResult(BaseModel):
    sweep_id: int | None  # None when the request was skipped
    skipped: str | None  # why nothing ran, e.g. another sweep is in progress
