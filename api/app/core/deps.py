from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal


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
