from typing import Literal
from pydantic import BaseModel


class CreateGameRequest:
    mode: Literal["hotseat", "vs_bot", "online"]
    player_x_id: int
    player_o_id: int


class PlayMoveRequest:
    pass


class GameResponse:
    pass


class GameDetailResponse:
    pass