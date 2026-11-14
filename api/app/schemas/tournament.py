from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from app.models.tournament import TournamentStatus
from app.schemas.common import reject_null


class TournamentCreate(BaseModel):
    # Bez statusa: svaki turnir pocinje kao draft
    name: str = Field(min_length=1, max_length=100)
    max_teams: int = Field(ge=2, le=64)
    # AwareDatetime trazi oznaku zone, npr. 2026-12-15T23:59:00+01:00. Baza
    # vrijednost bez zone ne bi odbila, nego bi je tumacila u svojoj zoni
    registration_deadline: AwareDatetime


class TournamentUpdate(BaseModel):
    # Status se ovdje ne mijenja: za to postoji zasebna ruta s pravilima prijelaza
    name: str | None = Field(default=None, min_length=1, max_length=100)
    max_teams: int | None = Field(default=None, ge=2, le=64)
    registration_deadline: AwareDatetime | None = None

    _not_null = field_validator(
        "name", "max_teams", "registration_deadline", mode="before"
    )(reject_null)


class TournamentStatusUpdate(BaseModel):
    status: TournamentStatus


class TournamentResponse(BaseModel):
    id: int
    name: str
    max_teams: int
    registration_deadline: datetime
    status: TournamentStatus
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
