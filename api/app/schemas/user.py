from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class UserResponse(BaseModel):
    # password_hash namjerno nije ovdje: polje kojeg nema u shemi ne moze izaci
    id: int
    username: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}
