from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.tournament import TournamentStatus
from app.models.user import User, UserRole
from app.schemas.tournament import (
    TournamentCreate,
    TournamentResponse,
    TournamentStatusUpdate,
    TournamentUpdate,
)
from app.services import tournament_service

router = APIRouter()


# Citanje smije svaki prijavljeni korisnik, pa je dovoljan get_current_user
@router.get("/", response_model=list[TournamentResponse])
async def list_tournaments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: TournamentStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await tournament_service.list_tournaments(db, user, status, limit, offset)


@router.get("/{tournament_id}", response_model=TournamentResponse)
async def get_tournament(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await tournament_service.get_tournament(db, tournament_id, user)


# Pisanje smije samo admin, pa ruta trazi require_role
@router.post("/", response_model=TournamentResponse, status_code=201)
async def create_tournament(
    body: TournamentCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    return await tournament_service.create_tournament(db, body, admin)


@router.patch("/{tournament_id}", response_model=TournamentResponse)
async def update_tournament(
    tournament_id: int,
    body: TournamentUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    return await tournament_service.update_tournament(db, tournament_id, body, admin)


@router.patch("/{tournament_id}/status", response_model=TournamentResponse)
async def change_status(
    tournament_id: int,
    body: TournamentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    return await tournament_service.change_status(db, tournament_id, body.status, admin)


@router.delete("/{tournament_id}", status_code=204)
async def delete_tournament(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    await tournament_service.delete_tournament(db, tournament_id, admin)
