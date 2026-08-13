from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.api.routers.customers import router as customer_router
from app.api.routers.pawn_contracts import router as pawn_contract_router
from app.api.routers.pawn_assets import router as pawn_asset_router
from app.api.routers.payments import router as payment_router

def create_application() -> FastAPI:
    application = FastAPI(
        title="Pawn Management API",
        version="0.1.0",
        description="Backend API for pawnshop management workflows.",
    )
    application.include_router(health_router)
    application.include_router(customer_router)
    application.include_router(pawn_contract_router)
    application.include_router(pawn_asset_router)
    application.include_router(payment_router)
    return application

app = create_application()

