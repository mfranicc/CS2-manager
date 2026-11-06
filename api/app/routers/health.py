from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter()


@router.get("/")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Provjera radi li aplikacija i veza s bazom."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
