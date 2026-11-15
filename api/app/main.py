from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.players import router as players_router
from app.routers.registrations import router as registrations_router
from app.routers.teams import router as teams_router
from app.routers.tournaments import router as tournaments_router


def create_app() -> FastAPI:
    app = FastAPI(title="CS2 Manager API")

    # Svaka pogreska izlazi u istom obliku: {"code": ..., "message": ...}
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    # Sve sto nijedan handler iznad ne uhvati: 500, ali u istom obliku
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(teams_router, prefix="/teams", tags=["teams"])
    app.include_router(
        players_router, prefix="/teams/{team_id}/players", tags=["players"]
    )
    app.include_router(tournaments_router, prefix="/tournaments", tags=["tournaments"])
    app.include_router(
        registrations_router,
        prefix="/tournaments/{tournament_id}/registrations",
        tags=["registrations"],
    )
    return app


app = create_app()
