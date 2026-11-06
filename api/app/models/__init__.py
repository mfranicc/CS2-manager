# Uvoz svih modela registrira ih u Base.metadata.
# autogenerate u Alembicu vidi samo modele koji su ovdje uvezeni.
from app.core.database import Base
from app.models.player import Player, PlayerRole
from app.models.registration import Registration
from app.models.team import Team
from app.models.tournament import Tournament, TournamentStatus
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "Player",
    "PlayerRole",
    "Registration",
    "Team",
    "Tournament",
    "TournamentStatus",
    "User",
    "UserRole",
]
