from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from app.routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="CS2 Manager API")

    # Svaka pogreska izlazi u istom obliku: {"code": ..., "message": ...}
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    app.include_router(health_router, prefix="/health", tags=["health"])
    return app


app = create_app()
