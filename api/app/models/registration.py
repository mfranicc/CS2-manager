from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.tournament import Tournament


class Registration(Base):
    """Prijava jednog tima na jedan turnir."""

    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id", "team_id", name="uq_registrations_tournament_team"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tournament: Mapped["Tournament"] = relationship(back_populates="registrations")
    team: Mapped["Team"] = relationship(back_populates="registrations")
