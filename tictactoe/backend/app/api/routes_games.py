from fastapi import Depends, FastAPI, APIRouter, HTTPException, Query
from typing import Literal, Any

from app.services.game_service import GameConflictError, GameNotFoundError, GameValidationError
from app.config import Settings, get_settings
from app.db
from app.api.schemas import CreateGameRequest, GameDetailResponse, GameResponse, GameListResponse, PlayMoveRequest

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

def __serialize_game(game:dict, *, move_number:int | None =None):
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

def _serialize_summary(row: dict) -> dict:
    return {
        "game_id": row["id"],
        "mode": row["mode"],
        "status": row["status"],
        "winner": row.get("winner"),
        "move_count": row.get("move_count", 0),
    }

@router.post("", response_model=GameResponse, status_code=201)
def create_game(body: CreateGameRequest, settings: Settings = Depends(get_settings_dep),):
    x_id = body.player_x_id if body.player_x_id is not none else HUMAN_PLAYER
    O_ID