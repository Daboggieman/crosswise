from datetime import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    mode: Literal["hotseat", "vs_bot", "online"]
    player_x_id: int
    player_o_id: int


class PlayMoveRequest(BaseModel):
    mark: Literal["X", "O"]
    cell: int = Field(ge=0, le=8)
    ply: int | None = None

class GameResponse(BaseModel):
    game_id: str
    mode: str
    status: str
    board: list[str]
    next_player: str | None
    winner: str | None
    winning_line: list[int] | None
    move_count: int
    move_number: int | None = None

class MoveOut(BaseModel):
    seq: int
    ply: int
    mark: str
    cell: int
    played_at: dt


class ActionOut(BaseModel):
    seq: int
    type: str
    actor: str
    payload: dict[str, Any] | None = None
    created_at: dt


class GameDetailResponse(GameResponse):
    moves: list[MoveOut]
    actions: list[ActionOut]

class GameListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None