from fastapi import FastAPI

from src.api import routes_analyze, routes_auth, routes_cases

app = FastAPI(title="Litigation Prep Assistant API")

app.include_router(routes_auth.router, prefix="/me", tags=["auth"])
app.include_router(routes_analyze.router, tags=["analyze"])
app.include_router(routes_cases.router, prefix="/history", tags=["history"])


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
