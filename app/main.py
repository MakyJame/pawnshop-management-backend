from fastapi import FastAPI

from app.api.routers.health import router as health_router

def create_application() -> FastAPI:
    application = FastAPI(
        title="Pawn Management API",
        version="0.1.0",
        description="Backend API for pawnshop management workflows.",
    )
    application.include_router(health_router)
        
    return application

app = create_application()

