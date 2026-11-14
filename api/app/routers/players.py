from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.player import PlayerRole
from app.models.user import User, UserRole
from app.schemas.player import PlayerCreate, PlayerResponse, PlayerUpdate
from app.services import player_service

# Putanje su bez prefiksa; /teams/{team_id}/players dodaje main.py
router = APIRouter()


@router.get("/", response_model=list[PlayerResponse])
async def list_players(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
    role: PlayerRole | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await player_service.list_players(db, team_id, user, role, limit, offset)


@router.post("/", response_model=PlayerResponse, status_code=201)
async def create_player(
    team_id: int,
    body: PlayerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    return await player_service.create_player(db, team_id, body, user)


@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(
    team_id: int,
    player_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    return await player_service.get_player(db, team_id, player_id, user)


@router.patch("/{player_id}", response_model=PlayerResponse)
async def update_player(
    team_id: int,
    player_id: int,
    body: PlayerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    return await player_service.update_player(db, team_id, player_id, body, user)


@router.delete("/{player_id}", status_code=204)
async def delete_player(
    team_id: int,
    player_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    await player_service.delete_player(db, team_id, player_id, user)
