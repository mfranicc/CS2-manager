from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.tournament import Tournament, TournamentStatus
from app.models.user import User, UserRole
from app.repositories import tournament_repo
from app.schemas.tournament import TournamentCreate, TournamentUpdate

# Jedini dopusteni sljedeci korak za svaki status; finished nema sljedeceg
NEXT_STATUS = {
    TournamentStatus.draft: TournamentStatus.registration_open,
    TournamentStatus.registration_open: TournamentStatus.ongoing,
    TournamentStatus.ongoing: TournamentStatus.finished,
}

# Statusi u kojima admin jos smije mijenjati podatke turnira
EDITABLE_STATUSES = {TournamentStatus.draft, TournamentStatus.registration_open}


def _ensure_deadline_in_future(deadline: datetime) -> None:
    # Usporedba u UTC-u: rok je timestamptz, pa nosi zonu
    if deadline <= datetime.now(timezone.utc):
        raise AppError("invalid_deadline", "Rok prijave mora biti u buducnosti", 400)


async def get_tournament(
    db: AsyncSession, tournament_id: int, current_user: User
) -> Tournament:
    tournament = await tournament_repo.get_by_id(db, tournament_id)
    # Draft je adminova priprema: manageru se ponasa kao da ne postoji
    hidden = (
        tournament is not None
        and tournament.status == TournamentStatus.draft
        and current_user.role != UserRole.admin
    )
    if tournament is None or hidden:
        raise AppError("not_found", "Turnir nije pronaden", 404)
    return tournament


async def list_tournaments(
    db: AsyncSession,
    current_user: User,
    status: TournamentStatus | None,
    limit: int,
    offset: int,
) -> list[Tournament]:
    include_drafts = current_user.role == UserRole.admin
    return await tournament_repo.get_all(db, status, include_drafts, limit, offset)


async def create_tournament(
    db: AsyncSession, body: TournamentCreate, current_user: User
) -> Tournament:
    _ensure_deadline_in_future(body.registration_deadline)
    tournament = Tournament(
        **body.model_dump(),
        status=TournamentStatus.draft,
        created_by_id=current_user.id,
    )
    return await tournament_repo.create(db, tournament)


async def update_tournament(
    db: AsyncSession, tournament_id: int, body: TournamentUpdate, current_user: User
) -> Tournament:
    tournament = await get_tournament(db, tournament_id, current_user)
    if tournament.status not in EDITABLE_STATUSES:
        raise AppError(
            "tournament_locked",
            "Turnir koji je u tijeku ili zavrsen ne mijenja se",
            409,
        )
    changes = body.model_dump(exclude_unset=True)
    if "registration_deadline" in changes:
        _ensure_deadline_in_future(changes["registration_deadline"])
    if "max_teams" in changes:
        # Kapacitet ne smije pasti ispod broja vec prijavljenih timova
        registered = await tournament_repo.count_registrations(db, tournament.id)
        if changes["max_teams"] < registered:
            raise AppError(
                "max_teams_too_low",
                f"Na turnir je vec prijavljeno {registered} timova",
                409,
            )
    for field, value in changes.items():
        setattr(tournament, field, value)
    await db.flush()
    return tournament


async def change_status(
    db: AsyncSession,
    tournament_id: int,
    new_status: TournamentStatus,
    current_user: User,
) -> Tournament:
    """Status ide samo naprijed, korak po korak: bez preskakanja i vracanja."""
    tournament = await get_tournament(db, tournament_id, current_user)
    allowed = NEXT_STATUS.get(tournament.status)
    if new_status != allowed:
        raise AppError(
            "invalid_status_transition",
            f"Prijelaz {tournament.status.value} -> {new_status.value} nije dopusten",
            409,
        )
    tournament.status = new_status
    await db.flush()
    return tournament


async def delete_tournament(
    db: AsyncSession, tournament_id: int, current_user: User
) -> None:
    tournament = await get_tournament(db, tournament_id, current_user)
    # Brise se samo priprema; objavljen turnir ima prijave i povijest
    if tournament.status != TournamentStatus.draft:
        raise AppError(
            "tournament_not_draft", "Moze se obrisati samo turnir u pripremi", 409
        )
    await tournament_repo.delete(db, tournament)
