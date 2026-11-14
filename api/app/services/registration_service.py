from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.registration import Registration
from app.models.tournament import Tournament, TournamentStatus
from app.models.user import User, UserRole
from app.repositories import player_repo, registration_repo, tournament_repo
from app.schemas.registration import RegistrationCreate
from app.services import team_service, tournament_service

# Tim mora imati punu postavu da bi se prijavio
MIN_PLAYERS_TO_REGISTER = 5


def _ensure_registration_open(tournament: Tournament) -> None:
    """Prijave i odjave vrijede samo dok je turnir otvoren i rok nije prosao."""
    if tournament.status != TournamentStatus.registration_open:
        raise AppError(
            "registration_not_open", "Prijave za ovaj turnir nisu otvorene", 409
        )
    # Usporedba u UTC-u: rok je timestamptz, pa nosi zonu
    if datetime.now(timezone.utc) >= tournament.registration_deadline:
        raise AppError("registration_closed", "Rok za prijavu je istekao", 409)


async def _get_registration_or_404(
    db: AsyncSession, tournament_id: int, registration_id: int
) -> Registration:
    registration = await registration_repo.get_by_id(db, registration_id)
    # Prijava drugog turnira pod ovom adresom ne postoji
    if not registration or registration.tournament_id != tournament_id:
        raise AppError("not_found", "Prijava nije pronadena", 404)
    return registration


def _ensure_registration_access(registration: Registration, current_user: User) -> None:
    if (
        current_user.role == UserRole.manager
        and registration.team.owner_id != current_user.id
    ):
        raise AppError("forbidden", "Prijava pripada timu drugog managera", 403)


async def list_registrations(
    db: AsyncSession, tournament_id: int, current_user: User, limit: int, offset: int
) -> list[Registration]:
    await tournament_service.get_tournament(db, tournament_id, current_user)
    # Admin vidi sve prijave, manager samo prijave svojih timova
    owner_id = current_user.id if current_user.role == UserRole.manager else None
    return await registration_repo.list_for_tournament(
        db, tournament_id, owner_id, limit, offset
    )


async def get_registration(
    db: AsyncSession, tournament_id: int, registration_id: int, current_user: User
) -> Registration:
    await tournament_service.get_tournament(db, tournament_id, current_user)
    registration = await _get_registration_or_404(db, tournament_id, registration_id)
    _ensure_registration_access(registration, current_user)
    return registration


async def create_registration(
    db: AsyncSession, tournament_id: int, body: RegistrationCreate, current_user: User
) -> Registration:
    # Zakljucani redak: do kraja transakcije nitko drugi ne prijavljuje na ovaj turnir
    tournament = await tournament_repo.get_by_id_for_update(db, tournament_id)
    if not tournament or tournament.status == TournamentStatus.draft:
        raise AppError("not_found", "Turnir nije pronaden", 404)

    # Pravila turnira prije svega ostaloga: zahtjev koji ne prolazi
    # ne pokrece ni dohvat tima ni provjeru vlasnistva
    _ensure_registration_open(tournament)

    # Oznaka tima stize u tijelu zahtjeva; i nju treba provjeriti, inace IDOR
    team = await team_service.get_team(db, body.team_id, current_user)

    if await player_repo.count_by_team(db, team.id) < MIN_PLAYERS_TO_REGISTER:
        raise AppError(
            "not_enough_players",
            f"Tim mora imati najmanje {MIN_PLAYERS_TO_REGISTER} igraca",
            409,
        )
    if await registration_repo.get_by_tournament_and_team(db, tournament.id, team.id):
        raise AppError("duplicate", "Tim je vec prijavljen na ovaj turnir", 409)
    registered = await tournament_repo.count_registrations(db, tournament.id)
    if registered >= tournament.max_teams:
        raise AppError("tournament_full", "Turnir je popunjen", 409)

    # UNIQUE(tournament_id, team_id) u bazi je zadnja obrana od dvostruke prijave
    try:
        registration = Registration(tournament_id=tournament.id, team_id=team.id)
        return await registration_repo.create(db, registration)
    except IntegrityError:
        raise AppError("duplicate", "Tim je vec prijavljen na ovaj turnir", 409)


async def delete_registration(
    db: AsyncSession, tournament_id: int, registration_id: int, current_user: User
) -> None:
    """Odjava tima: dopustena pod istim uvjetima kao i prijava."""
    tournament = await tournament_service.get_tournament(
        db, tournament_id, current_user
    )
    registration = await _get_registration_or_404(db, tournament_id, registration_id)
    _ensure_registration_access(registration, current_user)
    _ensure_registration_open(tournament)
    await registration_repo.delete(db, registration)
