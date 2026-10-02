from dataclasses import dataclass

EMPTY_BOARD = ("-",) * 9

@dataclass(frozen=True)
class State:
    board: tuple[str, ...]
    turn: str
    winner: str | None
    line: tuple[int, int, int] | None
    status: str


empty,mark_X,mark_O = "-","X","O"
# current_player = mark_X

state = State()

state = State(
    board=(
        empty, empty, empty,
        empty, empty, empty,
        empty, empty, empty
    ),
    turn=mark_X,
    winner = None,
    line = None,
    status = "playing"
)

winning_triples = (
    (0,1,2,),
    (3,4,5),
    (6,7,8),
    (0,3,6),
    (1,4,7),
    (2,5,8),
    (0,4,8),
    (2,4,6),
)

def board_from_string(value: str) -> tuple[str, ...]:
    return tuple(value)


def board_to_string(board: tuple[str, ...]) -> str:
    return "".join(board)