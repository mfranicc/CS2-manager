from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

app = FastAPI(title="CS2 Manager API")


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Provjera rade li aplikacija i veza s bazom."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
