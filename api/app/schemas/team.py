from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import reject_null


class TeamCreate(BaseModel):
    # Bez id, jer ga dodjeljuje baza, i bez owner_id, jer je to prijavljeni manager
    name: str = Field(min_length=1, max_length=100)
    tag: str = Field(min_length=1, max_length=10)


class TeamUpdate(BaseModel):
    # Sva polja neobavezna: PATCH salje samo ono sto se mijenja
    name: str | None = Field(default=None, min_length=1, max_length=100)
    tag: str | None = Field(default=None, min_length=1, max_length=10)

    _not_null = field_validator("name", "tag", mode="before")(reject_null)


class TeamResponse(BaseModel):
    id: int
    name: str
    tag: str
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
