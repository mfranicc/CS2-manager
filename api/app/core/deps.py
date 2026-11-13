from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.errors import AppError
from app.core.jwt import ExpiredSignatureError, InvalidTokenError, decode_token
from app.models.user import User, UserRole
from app.repositories import user_repo


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Jedna sesija, a time i jedna transakcija, po zahtjevu.

    commit tek kad cijela obrada prode; iznimka iz bilo kojeg sloja
    ponistava sve sto je zahtjev upisao.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# auto_error=False: bez zaglavlja dobivamo None i sami vracamo 401 u nasem obliku
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 1) je li token uopce poslan
    if credentials is None:
        raise AppError("invalid_credentials", "Nedostaje token", 401)
    # 2) moze li se dekodirati: potpis, istek, izdavatelj
    try:
        payload = decode_token(credentials.credentials)
    except ExpiredSignatureError:
        raise AppError("token_expired", "Token je istekao", 401)
    except InvalidTokenError:
        raise AppError("invalid_credentials", "Neispravan token", 401)
    # 3) je li pristupni, a ne refresh token
    if payload.get("type") != "access":
        raise AppError("invalid_credentials", "Neispravan token", 401)

    # Token opisuje stanje u trenutku izdavanja; korisnik je u medjuvremenu
    # mogao biti obrisan, pa zapis citamo iz baze
    user = await user_repo.get_by_id(db, int(payload["sub"]))
    if user is None:
        raise AppError("invalid_credentials", "Neispravan token", 401)
    return user


def require_role(*allowed_roles: UserRole):
    """Stvara ovisnost koja propusta samo navedene uloge.

    Uloga se cita iz zapisa u bazi, a ne iz tokena, pa promjena vrijedi odmah.
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppError("forbidden", "Nemate dozvolu za ovu akciju", 403)
        return current_user

    return checker
