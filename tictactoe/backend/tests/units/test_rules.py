import pytest #type:ignore
from app.engine.board import (
    State,
    empty,
    mark_O,
    mark_X,
    status_drawn,
    status_in_progress,
    status_won,
)
from app.engine.rules import (
    GameOverError,
    InvalidCellError,
    OccupiedCellError,
    WrongTurnError,
    apply_move,
    evaluate,
    legal_moves,
    new_game,
)


# --- new_game -------------------------------------------------------------


def test_new_game_starts_empty_with_x_to_move():
    state = new_game()
    assert state.board == (empty,) * 9
    assert state.turn == mark_X
    assert state.status == status_in_progress
    assert state.winner is None
    assert state.line is None


# --- legal_moves ----------------------------------------------------------


def test_legal_moves_all_empty_at_start():
    state = new_game()
    assert legal_moves(state) == [0, 1, 2, 3, 4, 5, 6, 7, 8]


def test_legal_moves_excludes_occupied_cells():
    state = apply_move(new_game(), mark_X, 4)
    moves = legal_moves(state)
    assert 4 not in moves
    assert len(moves) == 8


def test_legal_moves_empty_when_game_finished():
    won = apply_move(new_game(), mark_X, 0)
    won = apply_move(won, mark_O, 3)
    won = apply_move(won, mark_X, 1)
    won = apply_move(won, mark_O, 4)
    won = apply_move(won, mark_X, 2)  # X completes the top row
    assert won.status == status_won
    assert legal_moves(won) == []


# --- apply_move: errors ---------------------------------------------------


def test_apply_move_rejects_out_of_range_cell():
    state = new_game()
    with pytest.raises(InvalidCellError):
        apply_move(state, mark_X, 9)
    with pytest.raises(InvalidCellError):
        apply_move(state, mark_X, -1)


def test_apply_move_rejects_occupied_cell():
    state = apply_move(new_game(), mark_X, 4)
    with pytest.raises(OccupiedCellError):
        apply_move(state, mark_O, 4)


def test_apply_move_rejects_out_of_turn_mark():
    state = new_game()
    with pytest.raises(WrongTurnError):
        apply_move(state, mark_O, 0)


def test_apply_move_rejects_after_game_over():
    state = new_game()
    for player, cell in [(mark_X, 0), (mark_O, 3), (mark_X, 1), (mark_O, 4), (mark_X, 2)]:
        state = apply_move(state, player, cell)
    assert state.status == status_won
    with pytest.raises(GameOverError):
        apply_move(state, mark_O, 5)


# --- apply_move: legality and immutability --------------------------------


def test_apply_move_is_immutable():
    original = new_game()
    result = apply_move(original, mark_X, 4)
    # The original is untouched
    assert original.board == (empty,) * 9
    assert original.turn == mark_X
    # The result carries the move and flips the turn
    assert result.board[4] == mark_X
    assert result.turn == mark_O


def test_apply_move_flips_turn_after_each_move():
    state = new_game()
    state = apply_move(state, mark_X, 0)
    assert state.turn == mark_O
    state = apply_move(state, mark_O, 8)
    assert state.turn == mark_X


# --- evaluate -------------------------------------------------------------


def test_evaluate_finds_wins_for_both_players():
    x_wins = State(
        board=(mark_X, mark_X, mark_X, empty, empty, empty, empty, empty, empty),
        turn=mark_O,
    )
    result = evaluate(x_wins)
    assert result.status == status_won
    assert result.winner == mark_X
    assert result.line == (0, 1, 2)

    o_wins = State(
        board=(empty, empty, empty, mark_O, mark_O, mark_O, empty, empty, empty),
        turn=mark_X,
    )
    result = evaluate(o_wins)
    assert result.status == status_won
    assert result.winner == mark_O
    assert result.line == (3, 4, 5)


def test_evaluate_draw_on_full_board():
    full_draw = State(
        board=(
            mark_X, mark_O, mark_X,
            mark_O, mark_O, mark_X,
            mark_X, mark_X, mark_O,
        ),
        turn=mark_O,
    )
    assert evaluate(full_draw).status == status_drawn


def test_evaluate_in_progress_when_still_playable():
    state = State(
        board=(mark_X, empty, mark_O, empty, empty, empty, empty, empty, empty),
        turn=mark_O,
    )
    assert evaluate(state).status == status_in_progress
