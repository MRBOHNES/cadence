from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Check, Incident, Monitor, Sweep


class Seeder:
    """Builds fixtures in the test DB relative to a pinned 'now'."""

    def __init__(self, session: AsyncSession, now: datetime):
        self.session, self.now = session, now
        self.sweep_id = 0

    async def start(self) -> None:
        sweep = Sweep(started_at=self.now - timedelta(minutes=2), finished_at=self.now)
        self.session.add(sweep)
        await self.session.flush()
        self.sweep_id = sweep.id

    async def monitor(self, code: str, name: str | None = None, created_days_ago: float = 60) -> Monitor:
        m = Monitor(
            name=name or code.upper(),
            short_code=code,
            url=f"https://{code}.example",
            created_at=self.now - timedelta(days=created_days_ago),
        )
        self.session.add(m)
        await self.session.flush()
        return m

    def check(
        self,
        monitor: Monitor,
        *,
        ago: timedelta,
        ok: bool = True,
        latency: int | None = 100,
        status: int | None = None,
        error: str | None = None,
    ) -> Check:
        if status is None:
            status = 200 if ok else None
        c = Check(
            sweep_id=self.sweep_id,
            monitor_id=monitor.id,
            checked_at=self.now - ago,
            status_code=status,
            latency_ms=latency if (ok or status) else None,
            ok=ok,
            error=error if error else (None if ok else "timeout"),
        )
        self.session.add(c)
        return c

    def history(self, monitor: Monitor, *, days: int = 31, latency: int = 200, bad_at: set[int] | None = None):
        """One check every 6 hours going back `days` days. `bad_at` = indexes (0 = newest) that fail."""
        bad_at = bad_at or set()
        for i in range(days * 4 + 1):
            self.check(monitor, ago=timedelta(hours=6 * i), ok=i not in bad_at, latency=latency)

    def incident(self, monitor: Monitor, *, start_ago: timedelta, end_ago: timedelta | None, cause="timeout"):
        self.session.add(
            Incident(
                monitor_id=monitor.id,
                started_at=self.now - start_ago,
                resolved_at=None if end_ago is None else self.now - end_ago,
                cause=cause,
            )
        )

    async def commit(self) -> None:
        await self.session.commit()
