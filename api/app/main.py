from fastapi import FastAPI

from app.routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="CS2 Manager API")

    app.include_router(health_router, prefix="/health", tags=["health"])
    return app


app = create_app()
