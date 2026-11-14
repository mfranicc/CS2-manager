from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.player import PlayerRole
from app.schemas.common import reject_null


class PlayerCreate(BaseModel):
    # Bez id, jer ga dodjeljuje baza, i bez team_id, jer je vec u adresi rute
    nickname: str = Field(min_length=1, max_length=50)
    real_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: PlayerRole


class PlayerUpdate(BaseModel):
    # Sva polja neobavezna: PATCH salje samo ono sto se mijenja
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    # real_name smije biti null: tako se pravo ime brise
    real_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: PlayerRole | None = None

    _not_null = field_validator("nickname", "role", mode="before")(reject_null)


class PlayerResponse(BaseModel):
    id: int
    nickname: str
    real_name: str | None
    role: PlayerRole
    team_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
