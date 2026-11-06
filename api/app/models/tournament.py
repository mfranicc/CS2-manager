import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.registration import Registration
    from app.models.user import User


class TournamentStatus(str, enum.Enum):
    draft = "draft"
    registration_open = "registration_open"
    ongoing = "ongoing"
    finished = "finished"


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (CheckConstraint("max_teams >= 2", name="max_teams_min"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_teams: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(
            TournamentStatus,
            name="tournament_status",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=TournamentStatus.draft,
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    created_by: Mapped["User"] = relationship()
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
