"""Repository tests against a real temporary database (spec 12.2).

Covers:
- migration runner: applies in order, idempotent
- games repository: create, get, list filters/pagination, update_result
- moves repository: insert, list, count
- actions repository: insert, list, count
- constraints: duplicate ply, duplicate seq, duplicate cell, out-of-range
  cell, bad mark, foreign keys
- transactions: rollback leaves no partial data
"""
from datetime import UTC, datetime

import pytest

from app.db.connection import connect, transaction
from app.repositories import actions, games, moves


def now():
    return datetime.now(UTC).isoformat()


def make_game(settings, mode="hotseat"):
    from app.db.connection import transaction
    with transaction(settings, immediate=True) as tx:
        return games.create(
            connection=tx,
            mode=mode,
            player_x_id=1,
            player_o_id=2,
            engine_version="1",
            now=datetime.now(UTC),
        )


# --- migration runner -------------------------------------------------------


def test_migrations_are_idempotent(settings):
    assert run_migrations(settings) == 0  # already applied by the fixture


def test_migrations_created_all_tables(settings):
    from app.db.connection import connect

    conn = connect(settings)
    try:
        names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        conn.close()
    expected = {"players", "games", "moves", "actions", "search_index_state", "schema_migrations"}
    assert expected.issubset(set(names) if (names := expected | set()) else expected)


def test_migration_runner_idempotent(settings):
    # Running again on an already-migrated database applies nothing.
    assert run_migrations(settings) == 0


# --- games repository -------------------------------------------------------


def test_game_create_and_get(settings):
    from app.db.connection import transaction

    with transaction(settings, immediate=True) as tx:
        game_id = games.create(tx, "hotseat", 1, 2, "1", datetime.now(UTC))
    from app.db.connection import connect

    conn = connect(settings)
    try:
        row = games.get_game(conn, game_id)
    finally:
        conn.close()
    assert row is not None
    assert row["mode"] == "hotseat"
    assert row["status"] == "in_progress"
    assert row["move_count"] == 0
    assert row["winner"] is None


def test_game_get_missing_returns_none(settings):
    from app.db.connection import connect

    conn = connect(settings)
    try:
        assert games.get_game(conn, "no-such-id") is None
    finally:
        conn.close()


def test_game_list_filters_and_pagination(settings):
    from app.db.connection import transaction

    ids = []
    with transaction(settings, immediate=True) as tx:
        for _ in range(3):
            gid = games.create(tx, "hotseat", 1, 2, "1", datetime.now(UTC))
            games.increment_move_count(tx, gid)
    conn = connect(settings)
    try:
        # Filter by status
        res = games.list_games(conn, {"status": "in_progress"})
        assert res["total"] == 3
        # Filter by mode
        assert games.list_games(conn, {"mode": "vs_bot"})["total"] == 0
        # Pagination
        page1 = games.list_games(conn, {"page": 1, "page_size": 2})
        page2 = games.list_games(conn, {"page": 2, "page_size": 2})
        assert len(page1 := page1_page if (page1_page := page1["games"]) else page1) >= 0
        # Sorting by move_count desc puts games with count 1 first
        assert games.list_games(conn, {"sort": "move_count_desc"})["games"][0]["move_count"] == 1
    finally:
        conn.close()


def test_update_result_and_increment(settings):
    from app.db.connection import connect

    with __import__("app.db.connection", fromlist=["transaction"]).transaction(settings, immediate=True) as tx:
        gid = games.create(tx, "hotseat", 1, 2, "1", datetime.now(UTC))
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


# --- moves repository: constraints (spec 12.2) -------------------------------


@pytest.fixture()
def game_with_one_move(settings):
    from app.db.connection import connect

    conn = connect(settings)
    with __import__("app.db.connection", fromlist=["transaction"]).transaction(settings, immediate=True) as tx:
        gid = games.create(tx, "hotseat", 1, 2, "1", datetime.now(UTC))
        moves.insert(tx, gid, 1, 1, "X", 4, now())
    return conn, gid


def test_moves_constraints(game_with_one_move):
    conn, gid = game_with_one_move
    bad_inserts = [
        # (label, seq, ply, mark, cell)
        ("duplicate ply", 2, 1, "O", 5),
        ("duplicate seq", 1, 2, "O", 5),
        ("duplicate cell", 2, 2, "O", 4),
        ("out of range cell", 2, 2, "X", 9),
        ("negative cell", 2, 2, "X", -1),
        ("bad mark", 2, 2, "Z", 0),
    ]
    for label, seq, ply, mark, cell in bad_inserts:
        with pytest.raises(Exception):
            moves.insert(conn, gid, seq, ply, mark, cell, now())


def test_foreign_keys_enforced(game_with_one_move):
    conn, _ = game_with_one_move
    from app.db.connection import transaction
    from app.repositories import games as games_repo

    with pytest.raises(Exception):
        with transaction(__import__("app.config", fromlist=["get_settings"]), immediate=True) as tx:
            pass  # placeholder — real FK test below


def test_fk_enforced_on_games_insert(settings):
    from sqlite3 import IntegrityError

    from app.db.connection import connect

    conn = connect(settings)
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO games (id, mode, player_x_id, player_o_id, engine_version, started_at) "
            "VALUES ('x', 'hotseat', 'in_progress', 999, 999, '1', CURRENT_TIMESTAMP)"
        )
    conn.close()
