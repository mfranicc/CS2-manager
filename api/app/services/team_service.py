from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.team import Team
from app.models.user import User, UserRole
from app.repositories import team_repo
from app.schemas.team import TeamCreate, TeamUpdate


def ensure_team_access(current_user: User, team: Team) -> None:
    """Vlasnistvo: manager smije samo do svojih timova; admin do svih."""
    if current_user.role == UserRole.manager and team.owner_id != current_user.id:
        raise AppError("forbidden", "Nemate pristup timu drugog managera", 403)


async def get_team(db: AsyncSession, team_id: int, current_user: User) -> Team:
    # Prvo postoji li zapis, tek onda smije li ga posiljatelj vidjeti
    team = await team_repo.get_by_id(db, team_id)
    if not team:
        raise AppError("not_found", "Tim nije pronaden", 404)
    ensure_team_access(current_user, team)
    return team


async def list_teams(
    db: AsyncSession, current_user: User, limit: int, offset: int
) -> list[Team]:
    # Popis ne imenuje nijedan zapis, pa se ne odbija nego suzava
    owner_id = current_user.id if current_user.role == UserRole.manager else None
    return await team_repo.get_all(db, owner_id, limit, offset)


async def create_team(db: AsyncSession, body: TeamCreate, current_user: User) -> Team:
    # Provjera unaprijed daje jasnu poruku za uobicajen slucaj
    if await team_repo.get_by_name(db, body.name):
        raise AppError("duplicate", "Tim s tim imenom vec postoji", 409)
    # Ogranicenje UNIQUE u bazi hvata i dva istodobna zahtjeva koja produ provjeru
    try:
        team = Team(owner_id=current_user.id, **body.model_dump())
        return await team_repo.create(db, team)
    except IntegrityError:
        raise AppError("duplicate", "Tim s tim imenom vec postoji", 409)


async def update_team(
    db: AsyncSession, team_id: int, body: TeamUpdate, current_user: User
) -> Team:
    team = await get_team(db, team_id, current_user)
    # Samo poslana polja: izostalo polje ostaje kakvo je bilo
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    try:
        await db.flush()
    except IntegrityError:
        raise AppError("duplicate", "Tim s tim imenom vec postoji", 409)
    return team


async def delete_team(db: AsyncSession, team_id: int, current_user: User) -> None:
    team = await get_team(db, team_id, current_user)
    # Tim s prijavama se ne brise: povijest turnira mora ostati
    if await team_repo.has_registrations(db, team.id):
        raise AppError(
            "has_registrations", "Tim ima prijave na turnire i ne moze se obrisati", 409
        )
    await team_repo.delete(db, team)
