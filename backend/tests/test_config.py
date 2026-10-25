import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@h/db?sslmode=require&channel_binding=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
    ],
)
def test_database_url_is_normalised_for_asyncpg(raw, expected):
    assert Settings(database_url=raw).database_url == expected
