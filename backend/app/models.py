from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    short_code: Mapped[str] = mapped_column(String(3), unique=True)
    url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Sweep(Base):
    """One run of checking every monitor. Its id is the 'sweep #N' counter."""

    __tablename__ = "sweeps"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Check(Base):
    __tablename__ = "checks"
    __table_args__ = (Index("ix_checks_monitor_id_checked_at", "monitor_id", "checked_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sweep_id: Mapped[int] = mapped_column(ForeignKey("sweeps.id"))
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status_code: Mapped[int | None]
    latency_ms: Mapped[int | None]
    ok: Mapped[bool]
    error: Mapped[str | None] = mapped_column(Text)

    monitor: Mapped[Monitor] = relationship()


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cause: Mapped[str] = mapped_column(Text)

    monitor: Mapped[Monitor] = relationship()


class Achievement(Base):
    """Only unlock timestamps are stored; whether a rule currently holds is computed from checks."""

    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
