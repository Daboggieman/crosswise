from dataclasses import dataclass


empty, mark_X, mark_O = "-", "X", "O"

EMPTY_BOARD = (empty,) * 9


@dataclass(frozen=True)
class State:
    board: tuple[str, ...] = EMPTY_BOARD
    turn: str = mark_X
    winner: str | None = None
    line: tuple[int, int, int] | None = None
    status: str = "playing"


winning_triples = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


def board_from_string(value: str) -> tuple[str, ...]:
    return tuple(value)


def board_to_string(board: tuple[str, ...]) -> str:
    return "".join(board)