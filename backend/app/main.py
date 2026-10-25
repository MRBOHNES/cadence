from fastapi import FastAPI

from app.routers import internal

app = FastAPI(title="Cadence API", version="0.1.0")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(internal.router)
