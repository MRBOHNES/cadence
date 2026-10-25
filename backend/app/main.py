from fastapi import FastAPI

app = FastAPI(title="Cadence API", version="0.1.0")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
