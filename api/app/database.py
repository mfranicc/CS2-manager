from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Bazna klasa iz koje nasljeduju svi SQLAlchemy modeli."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI ovisnost: otvara sesiju za jedan zahtjev i zatvara je na kraju."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
