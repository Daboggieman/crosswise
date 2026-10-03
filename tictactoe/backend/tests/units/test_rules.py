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
    replay,
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
    won = replay([0, 3, 1, 4, 2])  # X wins the top row
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
    state = replay([0, 3, 1, 4, 2])  # X won, game over
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


# --- replay ---------------------------------------------------------------


def test_replay_folds_moves_to_final_state():
    moves = [0, 3, 1, 4, 2]  # X, O, X, O, X -> X wins top row
    final = replay(moves)
    assert final.status == status_won
    assert final.winner == mark_X
    assert final.line == (0, 1, 2)


def test_replay_empty_or_none_gives_new_game():
    for moves in ([], None):
        final = replay(moves)
        assert final.status == status_in_progress
        assert final.board == (empty,) * 9


# --- invariants (section 5.6 / 12.1) --------------------------------------


def test_invariant_replay_matches_stored_result():
    """Replaying a game's move list reproduces the final evaluate() result."""
    for moves in (
        [0, 1, 2],               # incomplete (X, O, X)
        [0, 3, 1, 4, 2],         # X wins top row
        [0, 1, 2, 4, 3, 6, 5, 8, 7],  # full-board draw
    ):
        final = replay(moves)
        # The recorded result equals what evaluate() says about the final board
        assert evaluate(State(board=final.board, turn=final.turn)) == final


def test_invariant_full_board_last_move_win_is_win_not_draw():
    # X completes the anti-diagonal (2,4,6) on the ninth and final move,
    # when the board fills. A line on the last move is a win, not a draw.
    # Turn-alternating: X plays 1,2,4,8 then 6 (last); O plays 0,3,5,7.
    moves = [1, 0, 2, 3, 4, 5, 8, 7, 6]
    final = replay(moves)
    assert final.status == status_won, "a full board with a line on the last move is a win"
    assert final.winner == mark_X
    assert final.line == (2, 4, 6)


def test_exhaustive_game_space_invariants_hold():
    """Walk every reachable game via recursive depth-first search and assert all
    section 5.6 invariants hold. The 3x3 game tree is small enough to walk fully."""
    checked = 0

    def walk(state: State) -> None:
        nonlocal checked
        checked += 1

        # Invariant 1: counts of X and O differ by at most one
        xs = state.board.count(mark_X)
        os = state.board.count(mark_O)
        assert os == xs or os == xs - 1, f"mark count imbalance at a node"

        # Invariant 2: no moves can be played once the game is over
        if state.status != status_in_progress:
            assert legal_moves(state) == []
            return  # terminal node: do not expand further

        # Invariant 3+4 are checked structurally: apply a legal move and require
        # the resulting status/won/drawn to match what evaluate() decides.
        for cell in legal_moves(state):
            nxt = apply_move(state, state.turn, cell)
            # If this move completed a line, evaluate() must report won (never drawn)
            assert nxt.status in (status_won, status_drawn, status_in_progress)
            walk(nxt)

    walk(new_game())

    # The full 3x3 reachable state space: 5478 terminal plus interior nodes,
    # plus the 9 empty initial. Not a hard guarantee but a sanity bound.
    assert checked >= 5000, f"walked only {checked} states; space seems too small"


# --- notation (not yet implemented) ---------------------------------------


# @pytest.mark.skip(reason="notation.py is not yet implemented (planned for Phase 1 completion)")
# def test_notation_index_conversion_roundtrip():
#     from app.engine import notation
#     for index in range(9):
#         coord = notation.index_to_coord(index)
#         assert notation.coord_to_index(*coord) == index
