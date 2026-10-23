from collections.abc import Callable
from datetime import UTC, datetime
from sqlite3 import IntegrityError

from app.db.connection import connect, transaction
from app.repositories.games import create, get_game, increment_move_count, update_result
from app.config import Settings
from app.repositories.moves import count_for_game, list_for_game, insert
from app.engine.rules import replay
from app.repositories import actions


class GameNotFoundError(Exception):
    """The requested game does not exist."""


class GameConflictError(Exception):
    """The requested move conflicts with the current game state."""


class GameValidationError(Exception):
    """The requested move is invalid."""

def utc_now() -> datetime:
    return datetime.now(UTC)

Clock = Callable[[], datetime]

def create_game(settings, mode, player_x_id, player_o_id, engine_version, now: datetime = utc_now()) -> str:
    connection = connect(settings)

    with transaction(settings, immediate=True):
        game_id = create(
            connection=connection, 
            mode=mode,
            player_x_id=player_x_id,
            player_o_id=player_o_id,
            engine_version=engine_version, 
            now = None)
        return game_id

def play_move(settings, game_id, mark, cell):
    connection = connect(settings)
    game = get_game(connection, game_id)

    if game is None:
        raise GameNotFoundError(f"Game with ID {game_id} not found.")

    existing_moves = list_for_game(connection, game_id)

    existing_moves = sorted(existing_moves, key=lambda move: move["seq"])
    cells = [move["cell"] for move in existing_moves]

    state = replay(cells)

    if state.status != "in_progress":
        raise GameConflictError("The game is already over.")
    if mark != state.turn:
        raise GameConflictError(f"It is not {mark}'s turn.")
    if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell <= 8:
        raise GameValidationError("Cell must be an integer between 0 and 8.")
    if cell in cells:
        raise GameValidationError(f"Cell {cell} is already occupied.")


    try:
        with transaction(settings, immediate=True):
            
            locked_game =get_game(connection, game_id)
            
            if locked_game is None:
                raise GameNotFoundError(
                    f"Game with ID {game_id} not found."
                    )

            current_moves = list_for_game(connection, game_id)
            current_moves = sorted(
                current_moves, 
                key=lambda move: move["seq"]
            )
            current_cells = [
                move["cell"] for move in current_moves
            ]

            current_state = replay(current_cells)

            if current_state.status != "in_progress":
                raise GameConflictError("The game is already over.")
            if mark != current_state.turn:
                raise GameConflictError(f"It is not {mark}'s turn.")
            if cell in current_cells:
                raise GameValidationError(f"Cell {cell} is already occupied.")

            max_move_seq = count_for_game(connection, game_id) or 0
            max_action_seq = actions.list_for_game(connection, game_id) or 0

            seq = max(max_move_seq, max_action_seq) + 1
            ply = count_for_game(connection, game_id)

            insert(
                connection = connection,
                game_id = game_id,
                seq = seq,
                ply = ply,
                mark = mark,
                cell = cell,
                played_at = utc_now(),
            )
            updated_cells = current_cells +[cell]
            new_state = replay(updated_cells)

            increment_move_count(connection, game_id)

            if new_state.status in ("won", "draw"):
                result_reason =(
                    "three in a row"
                    if new_state.status == "won"
                    else "draw"
                )

                update_result(
                    connection = connection,
                    game_id = game_id,
                    status = "finished`",
                    winner = new_state.winner,
                    result_reason = result_reason,
                    ended_at = utc_now()
                )
    except IntegrityError as exc:
        raise GameConflictError(
            "the move conflicts with an existing game move"
        ) from exc

    fresh_game = get_game(connection, game_id)
    fresh_moves = list_for_game(connection, game_id)
    fresh_moves = sorted (fresh_moves, key=lambda move: move["seq"])

    fresh_cells = [move["cell"] for move in fresh_moves]
    final_state = replay(fresh_cells)

    return {
        "game": fresh_game,
        "game_id": game_id,
        "status": final_state.status,
        "board": tuple(final_state.board),
        "next_player": final_state.turn,
        "winner": final_state.winner,
        "winning_line": final_state.line,
        "move_number": ply
    }

def get_game_service(settings, id):
    pass