"""Integration tests for the play_move service function (spec 6.4, 12.2).

Exercises the full transactional path: turn enforcement, occupied-cell rejection,
game-over rejection, seq sharing between moves and actions, winner/draw finalization,
and that a mid-transaction failure leaves no partial data.
"""
from datetime import UTC, datetime

import pytest

from app.db.connection import connect
from app.repositories import games, moves
from app.services import game_service
from app.services.game_service import (
    GameConflictError,
    GameNotFoundError,
    GameValidationError,
    play_move,
)


def now():
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_game(settings):
    return game_service.create_game(settings, "hotseat", 1, 2)


def get_rows(settings, gid):
    conn = connect(settings)
    try:
        return games.get_game(conn, gid)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------

def test_play_move_returns_updated_state(settings):
    gid = make_game(settings)
    result = play_move(settings, gid, "X", 4, now())
    assert result["move_number"] == 1
    assert result["next_player"] == "O"
    assert result["board"][4] == "X"
    assert result["status"] == "in_progress"


def test_play_move_persists_row(settings):
    gid = make_game(settings)
    play_move(settings, gid, "X", 4, now())
    row = get_rows(settings, gid)
    assert row["move_count"] == 1


def test_full_game_x_wins(settings):
    """X takes 0, 4, 8 — the main diagonal."""
    gid = make_game(settings)
    history = [("X", 0), ("O", 1), ("X", 4), ("O", 2), ("X", 8)]
    result = None
    for mark, cell in history:
        result = play_move(settings, gid, mark, cell, now())
    # The service returns the ENGINE's status ("won"); the DB row says "finished".
    assert result["status"] == "won"
    assert result["winner"] == "X"
    assert result["winning_line"] == (0, 4, 8)
    row = get_rows(settings, gid)
    assert row["status"] == "finished"
    assert row["move_count"] == 5


def test_full_game_draw(settings):
    """A known draw sequence on the 3x3 board."""
    gid = make_game(settings)
    history = [
        ("X", 0), ("O", 1), ("X", 2),
        ("O", 4), ("X", 6), ("O", 8),
        ("X", 7), ("O", 3), ("X", 5),
    ]
    result = None
    for mark, cell in history:
        result = play_move(settings, gid, mark, cell, now())
    # Engine reports "drawn"; the DB row stores "finished".
    assert result["status"] == "drawn"
    assert result["winner"] is None
    row = get_rows(settings, gid)
    assert row["status"] == "finished"
    assert row["result_reason"] == "draw"
    assert row["winner"] is None


# ---------------------------------------------------------------------------
# rejections
# ---------------------------------------------------------------------------

def test_play_move_missing_game_raises(settings):
    with pytest.raises(GameNotFoundError):
        play_move(settings, "no-such-game", "X", 0, now())


def test_play_move_wrong_turn_rejected(settings):
    gid = make_game(settings)
    with pytest.raises(GameConflictError):
        play_move(settings, gid, "O", 4, now())


def test_play_move_occupied_cell_rejected(settings):
    gid = make_game(settings)
    play_move(settings, gid, "X", 4, now())
    with pytest.raises(GameValidationError):
        play_move(settings, gid, "O", 4, now())


def test_play_move_out_of_range_cell_rejected(settings):
    gid = make_game(settings)
    with pytest.raises(GameValidationError):
        play_move(settings, gid, "X", 9, now())


def test_play_move_after_game_over_rejected(settings):
    gid = make_game(settings)
    for mark, cell in [("X", 0), ("O", 1), ("X", 4), ("O", 2), ("X", 8)]:
        play_move(settings, gid, mark, cell, now())
    with pytest.raises(GameConflictError):
        play_move(settings, gid, "O", 3, now())


def test_play_move_bad_mark_rejected(settings):
    gid = make_game(settings)
    with pytest.raises((GameValidationError, GameConflictError)):
        play_move(settings, gid, "Z", 0, now())


# ---------------------------------------------------------------------------
# seq sharing between moves and actions (spec 6.2 Option A)
# ---------------------------------------------------------------------------

def test_seq_is_shared_across_moves_and_actions(settings):
    """An action between moves pushes the next move's seq past it."""
    from app.db.connection import transaction
    from app.repositories import actions

    gid = make_game(settings)
    play_move(settings, gid, "X", 0, now())          # seq 1
    with transaction(settings, immediate=True) as tx:
        actions.insert(tx, gid, seq=2, type="offer_draw", actor="O", payload=None,
                       created_at=now().isoformat())  # seq 2
    result = play_move(settings, gid, "O", 4, now())   # must get seq 3
    assert result["move_number"] == 2

    conn = connect(settings)
    try:
        move_rows = moves.list_for_game(conn, gid)
        action_rows = actions.list_for_game(conn, gid)
    finally:
        conn.close()
    move_seqs = [m["seq"] for m in move_rows]
    action_seqs = [a["seq"] for a in action_rows]
    assert move_seqs == [1, 3]
    assert action_seqs == [2]


# ---------------------------------------------------------------------------
# no partial data on failure (spec 12.2)
# ---------------------------------------------------------------------------

def test_play_move_failure_leaves_no_partial_data(settings):
    """If the move insert succeeds but a later step fails, nothing persists.

    Simulate the later-step failure by exploding update_result. Note we must
    patch the name the SERVICE uses (game_service.update_result), not the
    repository module's own attribute — the service bound the function at
    import time.
    """
    gid = make_game(settings)
    # Set up a position where X's next move wins (X owns 0, 4; O owns 1, 2).
    play_move(settings, gid, "X", 0, now())
    play_move(settings, gid, "O", 1, now())
    play_move(settings, gid, "X", 4, now())
    play_move(settings, gid, "O", 2, now())
    move_count_before = get_rows(settings, gid)["move_count"]
    assert move_count_before == 4

    def exploding_update_result(*args, **kwargs):
        raise RuntimeError("simulated mid-transaction failure")

    original = game_service.update_result
    game_service.update_result = exploding_update_result
    try:
        with pytest.raises(RuntimeError):
            play_move(settings, gid, "X", 8, now())  # would win -> calls update_result
    finally:
        game_service.update_result = original

    row = get_rows(settings, gid)
    assert row["move_count"] == move_count_before  # no 5th move counted
    conn = connect(settings)
    try:
        # The four setup moves persist (they were separate committed
        # transactions); the point is the fifth move did NOT persist.
        assert len(moves.list_for_game(conn, gid)) == move_count_before
    finally:
        conn.close()
