from datetime import datetime

from pydantic import BaseModel


class RegistrationCreate(BaseModel):
    # Turnir je vec u adresi rute; tim se bira u tijelu zahtjeva
    team_id: int


class TeamBrief(BaseModel):
    """Suzeni tim unutar odgovora o prijavi: samo ono sto popis treba."""

    name: str
    tag: str

    model_config = {"from_attributes": True}


class RegistrationResponse(BaseModel):
    id: int
    tournament_id: int
    team_id: int
    created_at: datetime
    team: TeamBrief

    model_config = {"from_attributes": True}
