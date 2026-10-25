from collections.abc import Callable
from datetime import UTC, datetime
from sqlite3 import IntegrityError

from app.db.connection import connect, transaction
from app.engine.board import status_drawn, status_in_progress, status_won
from app.engine.rules import replay
from app.repositories.actions import max_seq_for_game as actions_max_seq
from app.repositories.games import create, get_game, increment_move_count, update_result
from app.repositories.moves import count_for_game as moves_count_for_game
from app.repositories.moves import insert as insert_move
from app.repositories.moves import list_for_game as list_moves_for_game
from app.repositories.moves import max_seq_for_game as moves_max_seq


class GameNotFoundError(Exception):
    """The requested game does not exist."""


class GameConflictError(Exception):
    """The requested move conflicts with the current game state."""


class GameValidationError(Exception):
    """The requested move is invalid."""


def utc_now() -> datetime:
    return datetime.now(UTC)


Clock = Callable[[], datetime]


def create_game(
    settings,
    mode: str,
    player_x_id: int,
    player_o_id: int,
    now: datetime | None = None,
) -> str:
    if now is None:
        now = utc_now()
    engine_version = settings.engine_version
    with transaction(settings, immediate=True) as tx:
        game_id = create(
            connection=tx,
            mode=mode,
            player_x_id=player_x_id,
            player_o_id=player_o_id,
            engine_version=engine_version,
            now=now,
        )
    return game_id


def get_game_service(settings, game_id):
    """Return a dict with game fields, board, moves, and actions."""
    conn = connect(settings)
    try:
        game = get_game(conn, game_id)
        if game is None:
            return None
        moves_rows = list_moves_for_game(conn, game_id)
        cells = [m["cell"] for m in sorted(moves_rows, key=lambda m: m["seq"])]
        state = replay(cells)
        return {
            "game": game,
            "board": tuple(state.board),
            "moves": moves_rows,
            "status": state.status,
            "winner": state.winner,
            "winning_line": state.line,
            "next_player": state.turn,
        }
    finally:
        conn.close()


def play_move(settings, game_id, mark, cell, now: datetime | None = None):
    if now is None:
        now = utc_now()

    # 1. Pre-transaction validation: load and check game state.
    game = get_game_service(settings, game_id)
    if game is None:
        raise GameNotFoundError(f"Game {game_id} not found.")

    existing_moves = game["moves"]
    cells = [m["cell"] for m in sorted(existing_moves, key=lambda m: m["seq"])]
    state = replay(cells)

    if state.status != status_in_progress:
        raise GameConflictError("The game is already over.")
    if mark != state.turn:
        raise GameConflictError(f"It is not {mark}'s turn.")
    if isinstance(cell, bool) or not isinstance(cell, int) or not (0 <= cell <= 8):
        raise GameValidationError("Cell must be an integer between 0 and 8.")
    if cell in cells:
        raise GameValidationError(f"Cell {cell} is already occupied.")

    try:
        # 2. Begin transaction and re-verify under lock.
        with transaction(settings, immediate=True) as tx:
            locked_game = get_game(tx, game_id)
            if locked_game is None:
                raise GameNotFoundError(f"Game {game_id} not found.")

            current_moves = list_moves_for_game(tx, game_id)
            current_cells = [m["cell"] for m in sorted(current_moves, key=lambda m: m["seq"])]
            current_state = replay(current_cells)

            if current_state.status != status_in_progress:
                raise GameConflictError("The game is already over.")
            if mark != current_state.turn:
                raise GameConflictError(f"It is not {mark}'s turn.")
            if cell in current_cells:
                raise GameValidationError(f"Cell {cell} is already occupied.")

            # 3. Allocate shared seq: highest seq used by any move or action + 1.
            seq = max(moves_max_seq(tx, game_id), actions_max_seq(tx, game_id)) + 1

            # 4. Insert the move.
            ply = moves_count_for_game(tx, game_id) + 1
            played_at = now.isoformat()
            insert_move(
                connection=tx,
                game_id=game_id,
                seq=seq,
                ply=ply,
                mark=mark,
                cell=cell,
                played_at=played_at,
            )

            # 5. Evaluate the new board state.
            updated_cells = current_cells + [cell]
            new_state = replay(updated_cells)

            # 6. Bump move_count.
            increment_move_count(tx, game_id)

            # 7. If game finished, update result.
            if new_state.status == status_won:
                update_result(
                    connection=tx,
                    game_id=game_id,
                    status="finished",
                    winner=new_state.winner,
                    result_reason="three_in_row",
                    ended_at=played_at,
                )
            elif new_state.status == status_drawn:
                update_result(
                    connection=tx,
                    game_id=game_id,
                    status="finished",
                    winner=None,
                    result_reason="draw",
                    ended_at=played_at,
                )

    except IntegrityError as exc:
        raise GameConflictError(
            "the move conflicts with an existing game move"
        ) from exc

    # 8. Fresh read after commit.
    fresh = get_game_service(settings, game_id)
    return {
        "game_id": game_id,
        "game": fresh["game"],
        "status": fresh["status"],
        "board": fresh["board"],
        "next_player": fresh["next_player"],
        "winner": fresh["winner"],
        "winning_line": fresh["winning_line"],
        "move_number": ply,
    }
