"""Map backend failures to clean HTTP errors with a uniform {"detail": ...} body."""

import logging
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, SQLAlchemyError

log = logging.getLogger("cadence")


def _error(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TimeoutError)
    @app.exception_handler(asyncio.TimeoutError)
    async def timeout_handler(_: Request, exc: Exception) -> JSONResponse:
        log.warning("Database timeout: %s", exc)
        return _error(504, "The database took too long to respond")

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    @app.exception_handler(OSError)
    async def unavailable_handler(_: Request, exc: Exception) -> JSONResponse:
        log.error("Database unavailable: %s", exc)
        return _error(503, "The database is unavailable")

    @app.exception_handler(DBAPIError)
    @app.exception_handler(SQLAlchemyError)
    async def bad_gateway_handler(_: Request, exc: Exception) -> JSONResponse:
        log.error("Database error: %s", exc)
        return _error(502, "The database returned an invalid response")

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error", exc_info=exc)
        return _error(500, "Internal server error")
