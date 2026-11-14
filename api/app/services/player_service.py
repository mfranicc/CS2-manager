from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.player import Player, PlayerRole
from app.models.user import User
from app.repositories import player_repo
from app.schemas.player import PlayerCreate, PlayerUpdate
from app.services import team_service

# Pet igraca u postavi i najvise dvije zamjene
MAX_PLAYERS_PER_TEAM = 7


async def list_players(
    db: AsyncSession,
    team_id: int,
    current_user: User,
    role: PlayerRole | None,
    limit: int,
    offset: int,
) -> list[Player]:
    # Tim iz adrese mora postojati, inace 404, i pripadati korisniku, inace 403
    await team_service.get_team(db, team_id, current_user)
    return await player_repo.get_by_team(db, team_id, role, limit, offset)


async def get_player(
    db: AsyncSession, team_id: int, player_id: int, current_user: User
) -> Player:
    await team_service.get_team(db, team_id, current_user)
    player = await player_repo.get_by_id(db, player_id)
    # Igrac drugog tima pod ovom adresom ne postoji
    if not player or player.team_id != team_id:
        raise AppError("not_found", "Igrac nije pronaden", 404)
    return player


async def create_player(
    db: AsyncSession, team_id: int, body: PlayerCreate, current_user: User
) -> Player:
    await team_service.get_team(db, team_id, current_user)
    if await player_repo.count_by_team(db, team_id) >= MAX_PLAYERS_PER_TEAM:
        raise AppError("team_full", f"Tim vec ima {MAX_PLAYERS_PER_TEAM} igraca", 409)
    if await player_repo.get_by_nickname(db, body.nickname):
        raise AppError("duplicate", "Igrac s tim nadimkom vec postoji", 409)
    try:
        player = Player(team_id=team_id, **body.model_dump())
        return await player_repo.create(db, player)
    except IntegrityError:
        raise AppError("duplicate", "Igrac s tim nadimkom vec postoji", 409)


async def update_player(
    db: AsyncSession,
    team_id: int,
    player_id: int,
    body: PlayerUpdate,
    current_user: User,
) -> Player:
    player = await get_player(db, team_id, player_id, current_user)
    # Samo poslana polja: izostalo polje ostaje kakvo je bilo
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(player, field, value)
    try:
        await db.flush()
    except IntegrityError:
        raise AppError("duplicate", "Igrac s tim nadimkom vec postoji", 409)
    return player


async def delete_player(
    db: AsyncSession, team_id: int, player_id: int, current_user: User
) -> None:
    player = await get_player(db, team_id, player_id, current_user)
    await player_repo.delete(db, player)
