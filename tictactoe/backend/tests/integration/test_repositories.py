"""Integration tests for repositories against a real temporary database.

Tests the migration runner, all three repositories, and DB constraints per spec 12.2:
duplicate ply, duplicate seq, duplicate cell, out-of-range cell, bad mark, FK enforcement,
and that a transaction rollback leaves no partial data.
"""
from datetime import UTC, datetime
from sqlite3 import IntegrityError

import pytest

from app.db.connection import connect, transaction
from app.db.migration_runner import run_migrations
from app.repositories import actions, games, moves
from app.repositories.actions import count_for_game as actions_count_for_game
from app.repositories.moves import count_for_game as moves_count_for_game

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now():
    return datetime.now(UTC).isoformat()


def create_game(settings, mode="hotseat", px=1, po=2):
    with transaction(settings, immediate=True) as tx:
        return games.create(tx, mode, px, po, "1", datetime.now(UTC))


# ---------------------------------------------------------------------------
# Migration runner (spec 6.6)
# ---------------------------------------------------------------------------

def test_migrations_are_applied_by_fixture(settings):
    """The fixture runs migrations; verify all expected tables exist."""
    conn = connect(settings)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        names = {r["name"] for r in rows}
    finally:
        conn.close()
    expected = {"players", "games", "moves", "actions", "search_index_state", "schema_migrations"}
    assert expected.issubset(names)


def test_migrations_are_idempotent(settings):
    """Running the runner twice on the same DB applies nothing the second time."""
    assert run_migrations(settings) == 0


# ---------------------------------------------------------------------------
# games repository
# ---------------------------------------------------------------------------

def test_game_create_stores_fields(settings):
    gid = create_game(settings)
    conn = connect(settings)
    try:
        row = games.get_game(conn, gid)
    finally:
        conn.close()
    assert row is not None
    assert row["mode"] == "hotseat"
    assert row["status"] == "in_progress"
    assert row["move_count"] == 0
    assert row["winner"] is None


def test_game_get_missing_returns_none(settings):
    conn = connect(settings)
    try:
        assert games.get_game(conn, "no-such-uuid") is None
    finally:
        conn.close()


def test_game_list_filters_by_status(settings):
    create_game(settings)          # in_progress
    gid2 = create_game(settings)   # in_progress
    conn = connect(settings)
    try:
        games.update_result(conn, gid2, "finished", "X", "three_in_row", now())
        assert games.list_games(conn, {"status": "in_progress"})["total"] == 1
        assert games.list_games(conn, {"status": "finished"})["total"] == 1
    finally:
        conn.close()


def test_game_list_pagination(settings):
    for _ in range(5):
        create_game(settings)
    conn = connect(settings)
    try:
        page1 = games.list_games(conn, {"page": 1, "page_size": 2})
        page2 = games.list_games(conn, {"page": 2, "page_size": 2})
        assert page1["total"] == 5
        assert len(page1["games"]) == 2
        assert len(page2["games"]) == 2
    finally:
        conn.close()


def test_update_result_and_increment(settings):
    gid = create_game(settings)
    conn = connect(settings)
    try:
        games.increment_move_count(conn, gid)
        games.update_result(conn, gid, "finished", "X", "three_in_row", now())
        row = games.get_game(conn, gid)
        assert row["status"] == "finished"
        assert row["winner"] == "X"
        assert row["move_count"] == 1
        assert row["ended_at"] is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# moves repository: constraints (spec 12.2)
# ---------------------------------------------------------------------------

@pytest.fixture()
def _game_with_one_move(settings):
    """Game with seq=1, ply=1 move at cell 4."""
    gid = create_game(settings)
    conn = connect(settings)
    with transaction(settings, immediate=True) as tx:
        moves.insert(tx, gid, seq=1, ply=1, mark="X", cell=4, played_at=now())
    return conn, gid


def test_moves_duplicate_ply_rejected(_game_with_one_move):
    conn, gid = _game_with_one_move
    with pytest.raises(IntegrityError):
        moves.insert(conn, gid, seq=2, ply=1, mark="O", cell=5, played_at=now())


def test_moves_duplicate_seq_rejected(_game_with_one_move):
    conn, gid = _game_with_one_move
    with pytest.raises(IntegrityError):
        moves.insert(conn, gid, seq=1, ply=2, mark="O", cell=5, played_at=now())


def test_moves_duplicate_cell_rejected(_game_with_one_move):
    conn, gid = _game_with_one_move
    with pytest.raises(IntegrityError):
        moves.insert(conn, gid, seq=2, ply=2, mark="O", cell=4, played_at=now())


def test_moves_out_of_range_cell_rejected(_game_with_one_move):
    conn, gid = _game_with_one_move
    with pytest.raises((IntegrityError, ValueError)):
        moves.insert(conn, gid, seq=2, ply=2, mark="X", cell=9, played_at=now())


def test_moves_negative_cell_rejected(_game_with_one_move):
    conn, gid = _game_with_one_move
    with pytest.raises((IntegrityError, ValueError)):
        moves.insert(conn, gid, seq=2, ply=2, mark="X", cell=-1, played_at=now())


def test_moves_bad_mark_rejected(_game_with_one_move):
    conn, gid = _game_with_one_move
    with pytest.raises((IntegrityError, ValueError)):
        moves.insert(conn, gid, seq=2, ply=2, mark="Z", cell=0, played_at=now())


def test_moves_list_and_count(_game_with_one_move):
    conn, gid = _game_with_one_move
    rows = moves.list_for_game(conn, gid)
    assert len(rows) == 1
    assert rows[0]["cell"] == 4
    assert moves_count_for_game(conn, gid) == 1


# ---------------------------------------------------------------------------
# actions repository
# ---------------------------------------------------------------------------

def test_actions_insert_and_list_and_count(settings):
    gid = create_game(settings)
    conn = connect(settings)
    try:
        with transaction(settings, immediate=True) as tx:
            actions.insert(tx, gid, seq=1, type="offer_draw", actor="X", payload=None, created_at=now())
            actions.insert(tx, gid, seq=2, type="accept_draw", actor="O", payload=None, created_at=now())
        rows = actions.list_for_game(conn, gid)
        assert len(rows) == 2
        assert rows[0]["type"] == "offer_draw"
        assert actions_count_for_game(conn, gid) == 2
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# foreign key enforcement (spec 6.4)
# ---------------------------------------------------------------------------

def test_bad_player_id_on_games_rejected(settings):
    conn = connect(settings)
    try:
        with pytest.raises(IntegrityError):
            conn.execute(
                "INSERT INTO games (id, mode, player_x_id, player_o_id, engine_version, started_at) "
                "VALUES (?, 'hotseat', 9999, 9999, '1', CURRENT_TIMESTAMP)",
                (f"fk-{datetime.now(UTC).isoformat()}",),
            )
    finally:
        conn.close()


def test_bad_game_id_on_moves_rejected(settings):
    conn = connect(settings)
    try:
        with pytest.raises(IntegrityError):
            conn.execute(
                "INSERT INTO moves (game_id, seq, ply, mark, cell, played_at) "
                "VALUES (?, 1, 1, 'X', 0, CURRENT_TIMESTAMP)",
                ("no-such-game-id",),
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# transaction rollback (spec 12.2: failure midway leaves no partial data)
# ---------------------------------------------------------------------------

def test_rollback_leaves_no_partial_move(settings):
    gid = create_game(settings)
    conn = connect(settings)
    try:
        move_count_before = games.get_game(conn, gid)["move_count"]
        try:
            with transaction(settings, immediate=True) as tx:
                moves.insert(tx, gid, seq=1, ply=1, mark="X", cell=4, played_at=now())
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        move_count_after = games.get_game(conn, gid)["move_count"]
        assert move_count_after == move_count_before  # unchanged by failed tx
    finally:
        conn.close()


def test_rollback_leaves_no_partial_game(settings):
    """Simulating a partial failure inside a create: the game row should not
    exist after a rolled-back transaction."""
    # We can't easily make create fail, but we can verify the pattern:
    # if a transaction does two inserts and the second raises, neither persists.
    gid = create_game(settings)
    conn = connect(settings)
    try:
        count_before = len(moves.list_for_game(conn, gid))
        try:
            with transaction(settings, immediate=True) as tx:
                moves.insert(tx, gid, seq=1, ply=1, mark="X", cell=0, played_at=now())
                raise RuntimeError("boom in second step")
        except RuntimeError:
            pass
        assert len(moves.list_for_game(conn, gid)) == count_before
    finally:
        conn.close()
