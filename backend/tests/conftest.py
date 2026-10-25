import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import asyncpg
import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import models  # noqa: F401  (registers tables)
from app.db import Base, get_session
from app.main import app
from app.routers.read import get_now
from tests.helpers import Seeder

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://cadence:cadence@localhost:5432/cadence_test"
)
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
_schema_ready = False


async def _ensure_database() -> None:
    """Create the test database (and tables) once per test run."""
    url = make_url(TEST_DATABASE_URL)
    admin = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port, database="postgres"
    )
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await admin.close()


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    global _schema_ready
    if not _schema_ready:
        await _ensure_database()
        _schema_ready = True
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Start every test from empty tables.
        await conn.execute(
            text("TRUNCATE achievements, incidents, checks, sweeps, monitors RESTART IDENTITY CASCADE")
        )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest.fixture
async def seed(session) -> Seeder:
    seeder = Seeder(session, NOW)
    await seeder.start()
    return seeder


@pytest.fixture
async def client(session_factory) -> AsyncIterator[httpx.AsyncClient]:
    async def override_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_now] = lambda: NOW
    # raise_app_exceptions=False lets us assert on the 5xx responses our handlers produce.
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
