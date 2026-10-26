from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import register_error_handlers
from app.routers import internal, read, sweep_now

app = FastAPI(title="Cadence API", version="0.1.0")

# Only the Vercel frontend may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["GET", "POST"],  # POST only for the public /sweep button
    allow_headers=[],
)
register_error_handlers(app)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(read.router)
app.include_router(sweep_now.router)
app.include_router(internal.router)
