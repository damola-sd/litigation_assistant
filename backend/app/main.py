from fastapi import FastAPI

from app.api.routers import analyze, health, history, me

app = FastAPI(title="Litigation Prep Assistant API")

app.include_router(health.router, tags=["health"])
app.include_router(me.router, prefix="/me", tags=["auth"])
app.include_router(analyze.router, tags=["analyze"])
app.include_router(history.router, prefix="/history", tags=["history"])
