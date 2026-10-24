from typing import Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime as dt


class CreateGameRequest(BaseModel):
    mode: Literal["hotseat", "vs_bot", "online"]
    player_x_id: int
    player_o_id: int


class PlayMoveRequest(BaseModel):
    mark: Literal["X", "O"]
    cell: int = Field(ge=0, le=8)
    ply: int | None

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
    payload: dict[str, Any]
    created_at: dt


class GameDetailResponse(BaseModel):
    moves: list[MoveOut]
    actions: list[ActionOut]

class GameListResponse:
    items: list[]
    total: int
    page: int
    page_size: int


class ErrorResponse:
    code: str
    message: str
    details: dict[str, Any] | None = None