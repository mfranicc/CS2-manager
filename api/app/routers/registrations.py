from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.registration import RegistrationCreate, RegistrationResponse
from app.services import registration_service

# Putanje su bez prefiksa; /tournaments/{tournament_id}/registrations dodaje main.py
router = APIRouter()


@router.get("/", response_model=list[RegistrationResponse])
async def list_registrations(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await registration_service.list_registrations(
        db, tournament_id, user, limit, offset
    )


@router.post("/", response_model=RegistrationResponse, status_code=201)
async def create_registration(
    tournament_id: int,
    body: RegistrationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.manager)),
):
    return await registration_service.create_registration(db, tournament_id, body, user)


@router.get("/{registration_id}", response_model=RegistrationResponse)
async def get_registration(
    tournament_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    return await registration_service.get_registration(
        db, tournament_id, registration_id, user
    )


@router.delete("/{registration_id}", status_code=204)
async def delete_registration(
    tournament_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    await registration_service.delete_registration(
        db, tournament_id, registration_id, user
    )
