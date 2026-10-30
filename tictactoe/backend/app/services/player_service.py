from app.repositories.players import (
    get_by_name as players_get_by_name,
    create as players_create
)
from app.db.connection import transaction as connection_transaction
from app.services.game_service import utc_now

class PlayerValidationError(Exception):
    """raised when a player name is invalid"""

def get_or_create_player(settings, display_name, now=None):
    
    if now is None:
            now = utc_now()
    
    if not display_name or not display_name.strip():
        raise PlayerValidationError("Player name cannot be empty.")
    
    display_name = display_name.strip()

    with connection_transaction(settings, immediate=True) as connection:
        player = players_get_by_name(connection, display_name)
        
        if player is not None:
            return player["id"]
        
        return players_create(
            connection,
            display_name,
            "human",
            now,
        )