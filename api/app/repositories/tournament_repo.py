from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registration import Registration
from app.models.tournament import Tournament, TournamentStatus


async def get_by_id(db: AsyncSession, tournament_id: int) -> Tournament | None:
    return await db.get(Tournament, tournament_id)


async def get_by_id_for_update(
    db: AsyncSession, tournament_id: int
) -> Tournament | None:
    # SELECT ... FOR UPDATE: redak turnira ostaje zakljucan do kraja transakcije,
    # pa dvije istodobne prijave ne mogu obje proci provjeru kapaciteta
    return await db.get(Tournament, tournament_id, with_for_update=True)


async def get_all(
    db: AsyncSession,
    status: TournamentStatus | None,
    include_drafts: bool,
    limit: int,
    offset: int,
) -> list[Tournament]:
    stmt = select(Tournament)
    if status is not None:
        stmt = stmt.where(Tournament.status == status)
    if not include_drafts:
        # Sakrivanje u upitu: draft turniri ni ne izlaze iz baze
        stmt = stmt.where(Tournament.status != TournamentStatus.draft)
    stmt = (
        stmt.order_by(Tournament.registration_deadline, Tournament.id)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_registrations(db: AsyncSession, tournament_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(Registration)
        .where(Registration.tournament_id == tournament_id)
    )
    return await db.scalar(stmt)


async def create(db: AsyncSession, tournament: Tournament) -> Tournament:
    db.add(tournament)
    await db.flush()
    return tournament


async def delete(db: AsyncSession, tournament: Tournament) -> None:
    await db.delete(tournament)
    await db.flush()
