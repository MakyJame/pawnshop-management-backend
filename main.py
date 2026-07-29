from fastapi import FastAPI

from app.api.routers.health import router as health_router

app.include(health_router)
