from fastapi import (
    Depends, 
    FastAPI,
    APIRouter, 
    HTTPException, 
    Query
)
from typing import (Literal, Any)

from app.services.game_service import (
    GameConflictError, 
    GameNotFoundError, 
    GameValidationError, 
    create_game as gameservice_create_game,
    get_game_service as gameservice_get_game_service,
    play_move as gameservice_play_move
)
from app.config import (
    Settings, 
    get_settings
)
from app.db.connection import (
    connect,
    transaction
)
from app.api.schemas import(
    CreateGameRequest, 
    GameDetailResponse, 
    GameResponse, 
    GameListResponse, 
    PlayMoveRequest,
)
from app.repositories.games import(
    list_games as games_list_games
)

router = APIRouter(prefix="/games", tags=["games"])

HUMAN_PLAYER_ID = 1
EMPTY_CELL = ""
_ENGINE_TO_API_STATUS ={
    "won": "finished",
    "drawn": "finished"
}

def get_settings_dep() -> Settings:
    return get_settings()

def _http_error(status_code: int, code: str, message:str) -> HTTPException:
    return HTTPException(
        status_code = status_code,
        detail={"code": code, "message": message, "details": None,}
    )

def _build_board(moves: list[dict]) -> list[str]:
    board = [EMPTY_CELL] * 9
    for m in moves:
        board[m["cell"]] = m["mark"]
    return board

def _serialize_game(game:dict, *, move_number:int | None =None):
    moves = game.get("moves", [])
    in_progress = game["status"] == "in_Progress"
    return {
        "game_id": game["id"],
        "mode": game["mode"],
        "status": game["status"],
        "board": _build_board(moves),
        "next_player": ("X" if len(moves) % 2 == 0 else "O") if in_progress else None,
        "winner": game.get("winner"),
        "winning_line": game.get("winning_line"),
        "move_count": len(moves),
        "move_number": move_number,
    }

def _serialize_summary(row):
    return {
        "game_id": row["id"],
        "mode": row["mode"],
        "status": row["status"],
        "winner": row.get("winner"),
        "move_count": row.get("move_count", 0),
    }

@router.post("", response_model=GameResponse, status_code=201)
def create_game(body: CreateGameRequest, settings: Settings = Depends(get_settings_dep),):
    x_id = body.player_x_id if body.player_x_id is not None else HUMAN_PLAYER_ID
    o_id = body.player_o_id if body.player_o_id is not None else HUMAN_PLAYER_ID

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
    settings: Settings = Depends(get_settings_dep),
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
        rows, total = games_list_games(conn, filters)
    return {
        "items": [_serialize_summary(dict(r)) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game(
    game_id: str,
    settings: Settings = Depends(get_settings_dep),
):
    game = gameservice_get_game_service(settings, game_id)
    if game is None:
        raise GameNotFoundError(f"Game {game_id} not found.")

    return {
        **_serialize_game(game),
        "moves": game.get("moves", []),
        "actions": game.get("actions", []),
    }


@router.post("/{game_id}/moves", response_model=GameResponse)
def play_move(
    game_id: str,
    body: PlayMoveRequest,
    settings: Settings = Depends(get_settings_dep),
):
    try:
        result = gameservice_play_move(
            settings, game_id, body.mark, body.cell, body.ply
        )
    except GameNotFoundError as exc:
        raise _http_error(404, "game_not_found", str(exc))
    except GameValidationError as exc:
        raise _http_error(422, "validation_error", str(exc))
    except GameConflictError as exc:
        raise _http_error(409, "conflict", str(exc))

    game = gameservice_get_game_service(settings, game_id)
    api_status = _ENGINE_TO_API_STATUS.get(result["status"], result["status"])

    return {
        "game_id": game_id,
        "mode": game["mode"],
        "status": api_status,
        "board": result["board"],
        "next_player": result["next_player"],
        "winner": result["winner"],
        "winning_line": result["winning_line"],
        "move_count": len(game.get("moves", [])),
        "move_number": result["move_number"],
    }