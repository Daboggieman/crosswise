from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.schemas import (
    ActionOut,
    CreateGameRequest,
    GameDetailResponse,
    GameListResponse,
    GameResponse,
    MoveOut,
    PlayMoveRequest,
)
from app.config import Settings, get_settings
from app.db.connection import connect
from app.repositories.games import list_games as repo_list_games
from app.services.game_service import (
    GameNotFoundError,
    GameValidationError
)
from app.services.game_service import (
    create_game as gameservice_create_game,
)
from app.services.game_service import (
    get_game_service as gameservice_get_game_service,
)
from app.services.game_service import (
    play_move as gameservice_play_move,
)
from app.services.player_service import (
    get_or_create_player
)

router = APIRouter(prefix="/games", tags=["games"])

EMPTY_CELL = ""
_ENGINE_TO_API_STATUS ={
    "won": "finished",
    "drawn": "finished"
}

def get_settings_dep() -> Settings:
    return get_settings()

def _build_board(moves: list[dict]) -> list[str]:
    board = [EMPTY_CELL] * 9
    for m in moves:
        board[m["cell"]] = m["mark"]
    return board

def _serialize_game(top_level: dict, *, move_number: int | None = None):
    game_row = top_level["game"]
    moves = top_level.get("moves", [])
    return {
        "game_id": game_row["id"],
        "mode": game_row["mode"],
        "status": game_row["status"],
        "board": _build_board(moves),
        "next_player": top_level.get("next_player"),
        "winner": top_level.get("winner"),
        "winning_line": top_level.get("winning_line"),
        "move_count": game_row["move_count"],
        "move_number": move_number,
    }

def _serialize_summary(row):
    return {
        "game_id": row["id"],
        "mode": row["mode"],
        "status": row["status"],
        "winner": row["winner"],
        "move_count": row["move_count"],
    }

@router.post("", response_model=GameResponse, status_code=201)
def create_game(body: CreateGameRequest, settings: Settings = Depends(get_settings)):  # noqa: B008
    if body.player_x_id is not None:
        x_id = body.player_x_id
    elif body.player_x_name is not None and body.player_x_name.strip():
        x_id = get_or_create_player(settings, body.player_x_name)
    else:
        raise GameValidationError("player_x_id or player_x_name is required.")

    if body.player_o_id is not None:
        o_id = body.player_o_id
    elif body.player_o_name is not None and body.player_o_name.strip():
        o_id = get_or_create_player(settings, body.player_o_name)
    else:
        raise GameValidationError("player_o_id or player_o_name is required.")

    game_id = gameservice_create_game(settings, body.mode, x_id, o_id)
    game = gameservice_get_game_service(settings, game_id)

    return _serialize_game(game)

@router.get("", response_model=GameListResponse)
def list_games(
    status: str | None = None,
    winner: str | None = None,
    mode: Literal["hotseat", "vs_bot", "online"] | None = None,
    player: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = None,
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    candidates = {
        "status": status,
        "winner": winner,
        "mode": mode,
        "player": player,
        "page": page,
        "page_size": page_size,
        "sort": sort,
    }
    filters = {k: v for k, v in candidates.items() if v is not None}

    with connect(settings) as conn:
        result = repo_list_games(conn, filters)
    rows = result["games"]
    total = result["total"]
    return {
        "items": [_serialize_summary(dict(r)) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game(game_id: str, settings: Settings = Depends(get_settings)):  # noqa: B008
    game = gameservice_get_game_service(settings, game_id)
    if game is None:
        raise GameNotFoundError(f"Game {game_id} not found.")
    return {
        **_serialize_game(game),
        "moves": [MoveOut(**dict(m)) for m in game.get("moves", [])],
        "actions": [ActionOut(**dict(a)) for a in game.get("actions", [])],
    }


@router.post("/{game_id}/moves", response_model=GameResponse)
def play_move(
    game_id: str,
    body: PlayMoveRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    # Service exceptions (GameNotFoundError/GameValidationError/GameConflictError)
    # propagate to the app-wide handlers in app/api/errors.py, which map them
    # to 404/422/409 with the spec's error shape.
    result = gameservice_play_move(
        settings, game_id, body.mark, body.cell
    )

    game = gameservice_get_game_service(settings, game_id)
    api_status = _ENGINE_TO_API_STATUS.get(result["status"], result["status"])

    return {
        "game_id": game_id,
        "mode": game["game"]["mode"],
        "status": api_status,
        "board": list(result["board"]),
        "next_player": result["next_player"],
        "winner": result["winner"],
        "winning_line": list(result["winning_line"]) if result["winning_line"] else None,
        "move_count": game["game"]["move_count"],
        "move_number": result["move_number"],
    }