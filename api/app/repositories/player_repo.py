from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player, PlayerRole


async def get_by_id(db: AsyncSession, player_id: int) -> Player | None:
    return await db.get(Player, player_id)


async def get_by_nickname(db: AsyncSession, nickname: str) -> Player | None:
    result = await db.execute(select(Player).where(Player.nickname == nickname))
    return result.scalar_one_or_none()


async def get_by_team(
    db: AsyncSession,
    team_id: int,
    role: PlayerRole | None,
    limit: int,
    offset: int,
) -> list[Player]:
    # Upit se gradi postupno: tim uvijek, uloga samo ako je filtar poslan
    stmt = select(Player).where(Player.team_id == team_id)
    if role is not None:
        stmt = stmt.where(Player.role == role)
    stmt = stmt.order_by(Player.id).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_by_team(db: AsyncSession, team_id: int) -> int:
    stmt = select(func.count()).select_from(Player).where(Player.team_id == team_id)
    return await db.scalar(stmt)


async def create(db: AsyncSession, player: Player) -> Player:
    db.add(player)
    await db.flush()
    return player


async def delete(db: AsyncSession, player: Player) -> None:
    await db.delete(player)
    await db.flush()
