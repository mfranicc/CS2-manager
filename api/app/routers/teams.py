from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate
from app.services import team_service

router = APIRouter()


@router.get("/", response_model=list[TeamResponse])
async def list_teams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await team_service.list_teams(db, user, limit, offset)


@router.post("/", response_model=TeamResponse, status_code=201)
async def create_team(
    body: TeamCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    return await team_service.create_team(db, body, user)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    return await team_service.get_team(db, team_id, user)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    body: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    return await team_service.update_team(db, team_id, body, user)


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    await team_service.delete_team(db, team_id, user)
