from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# engine drzi skup otvorenih veza prema bazi
engine = create_async_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False: nakon commita objekti zadrzavaju ucitane vrijednosti,
# pa ih shema odgovora moze procitati bez novog upita
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Predvidljiva imena ogranicenja, da migracije (i njihovo vracanje) znaju sto obrisati.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Bazna klasa iz koje nasljeduju svi SQLAlchemy modeli."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
