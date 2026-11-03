import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.team import Team


class PlayerRole(str, enum.Enum):
    igl = "igl"
    awper = "awper"
    entry = "entry"
    rifler = "rifler"
    support = "support"
    lurker = "lurker"


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    real_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[PlayerRole] = mapped_column(
        Enum(PlayerRole, name="player_role", native_enum=False, create_constraint=True),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    team: Mapped["Team"] = relationship(back_populates="players")
