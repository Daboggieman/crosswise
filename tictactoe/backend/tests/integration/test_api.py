"""API integration tests using FastAPI's test client (spec §12.3).

Tests the full happy path (create, play to win, play to draw), every error
path and its status code, pagination and filters, and that retried requests
do not double-apply.
"""
import os
import sys
import uuid
from pathlib import Path

# Make `app` importable regardless of where pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from starlette.testclient import TestClient

from app.config import get_settings
from app.db.migration_runner import run_migrations
from app.main import create_app

# ---------------------------------------------------------------------------
# Per-test database fixture
# ---------------------------------------------------------------------------

def get_client():
    """Return a TestClient backed by a fresh temporary database."""
    db_url = f"/tmp/crosswise-api-test-{uuid.uuid4().hex}.db"
    os.environ["DATABASE_URL"] = db_url
    os.environ["MIGRATIONS_DIR"] = str(BACKEND_DIR / "migrations")
    s = get_settings()
    run_migrations(s)
    app = create_app()
    client = TestClient(app)
    # Tear down the temp DB after the test.
    client._app = None   # signal to tear down
    return client, db_url


def teardown_db(db_url):
    for suffix in ("", "-wal", "-shm"):
        p = Path(db_url + suffix)
        if p.exists():
            p.unlink()


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------

def test_health_returns_200():
    client, db = get_client()
    try:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
    finally:
        teardown_db(db)


# ---------------------------------------------------------------------------
# create game
# ---------------------------------------------------------------------------

def test_create_game_returns_201():
    client, db = get_client()
    try:
        r = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1})
        assert r.status_code == 201
        body = r.json()
        assert body["game_id"] is not None
        assert body["mode"] == "hotseat"
        assert body["status"] == "in_progress"
        assert body["board"] == ["", "", "", "", "", "", "", "", ""]
        assert body["next_player"] == "X"
        assert body["winner"] is None
        assert body["winning_line"] is None
        assert body["move_count"] == 0
    finally:
        teardown_db(db)


def test_create_game_bad_mode_returns_422():
    client, db = get_client()
    try:
        r = client.post("/api/v1/games", json={"mode": "invalid_mode", "player_x_id": 1, "player_o_id": 1})
        assert r.status_code == 422
        assert r.json()["code"] == "validation_error"
    finally:
        teardown_db(db)


# ---------------------------------------------------------------------------
# play move — happy path
# ---------------------------------------------------------------------------

def test_play_move_returns_updated_board():
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 4})
        assert r.status_code == 200
        body = r.json()
        assert body["board"][4] == "X"
        assert body["next_player"] == "O"
        assert body["status"] == "in_progress"
        assert body["move_number"] == 1
    finally:
        teardown_db(db)


def test_full_game_x_wins():
    """X takes 0, 4, 8 — the main diagonal."""
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        for mark, cell in [("X", 0), ("O", 1), ("X", 4), ("O", 2), ("X", 8)]:
            r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": mark, "cell": cell})
            assert r.status_code == 200, f"move {mark}/{cell} failed: {r.json()}"
        body = r.json()
        assert body["status"] == "finished"
        assert body["winner"] == "X"
        assert body["winning_line"] == [0, 4, 8]
    finally:
        teardown_db(db)


def test_full_game_draw():
    """A known draw sequence on the 3x3 board."""
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        for mark, cell in [
            ("X", 0), ("O", 1), ("X", 2),
            ("O", 4), ("X", 6), ("O", 8),
            ("X", 7), ("O", 3), ("X", 5),
        ]:
            r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": mark, "cell": cell})
            assert r.status_code == 200
        body = r.json()
        assert body["status"] == "finished"
        assert body["winner"] is None
    finally:
        teardown_db(db)


# ---------------------------------------------------------------------------
# play move — error paths
# ---------------------------------------------------------------------------

def test_play_move_wrong_turn_returns_409():
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "O", "cell": 4})
        assert r.status_code == 409
        assert r.json()["code"] == "conflict"
    finally:
        teardown_db(db)


def test_play_move_occupied_cell_returns_422():
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 4})
        r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "O", "cell": 4})
        assert r.status_code == 422
        assert r.json()["code"] == "validation_error"
    finally:
        teardown_db(db)


def test_play_move_out_of_range_returns_422():
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 99})
        assert r.status_code == 422
    finally:
        teardown_db(db)


def test_play_move_after_game_over_returns_409():
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        for mark, cell in [("X", 0), ("O", 1), ("X", 4), ("O", 2), ("X", 8)]:
            client.post(f"/api/v1/games/{gid}/moves", json={"mark": mark, "cell": cell})
        r = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "O", "cell": 3})
        assert r.status_code == 409
        assert r.json()["code"] == "conflict"
    finally:
        teardown_db(db)


def test_play_move_missing_game_returns_404():
    client, db = get_client()
    try:
        r = client.post("/api/v1/games/no-such-id/moves", json={"mark": "X", "cell": 0})
        assert r.status_code == 404
        assert r.json()["code"] == "game_not_found"
    finally:
        teardown_db(db)


def test_get_game_missing_returns_404():
    client, db = get_client()
    try:
        r = client.get("/api/v1/games/no-such-id")
        assert r.status_code == 404
        assert r.json()["code"] == "game_not_found"
    finally:
        teardown_db(db)


# ---------------------------------------------------------------------------
# idempotency (spec §7.4 / §12.3)
# ---------------------------------------------------------------------------

def test_repeated_move_does_not_double_apply():
    """A retried request with the same ply does not create duplicate moves."""
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        r1 = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 4, "ply": 1})
        assert r1.status_code == 200
        # Retry the exact same move with the same ply.
        r2 = client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 4, "ply": 1})
        assert r2.status_code in (200, 409)  # either accepted as no-op or rejected
        # Verify only one move was recorded.
        detail = client.get(f"/api/v1/games/{gid}").json()
        assert detail["move_count"] == 1
    finally:
        teardown_db(db)


# ---------------------------------------------------------------------------
# get game
# ---------------------------------------------------------------------------

def test_get_game_returns_board_and_moves():
    client, db = get_client()
    try:
        gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 0})
        client.post(f"/api/v1/games/{gid}/moves", json={"mark": "O", "cell": 1})
        r = client.get(f"/api/v1/games/{gid}")
        assert r.status_code == 200
        body = r.json()
        assert body["board"][0] == "X"
        assert body["board"][1] == "O"
        assert len(body["moves"]) == 2
        assert len(body["actions"]) == 0
        # GameResponse fields are also present.
        assert body["mode"] == "hotseat"
        assert body["status"] == "in_progress"
    finally:
        teardown_db(db)


# ---------------------------------------------------------------------------
# list games
# ---------------------------------------------------------------------------

def test_list_games_returns_items_and_total():
    client, db = get_client()
    try:
        for _ in range(3):
            gid = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
            client.post(f"/api/v1/games/{gid}/moves", json={"mark": "X", "cell": 0})
        r = client.get("/api/v1/games")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert all(item["move_count"] == 1 for item in body["items"])
    finally:
        teardown_db(db)


def test_list_games_filters_by_status():
    client, db = get_client()
    try:
        client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        gid_finished = client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1}).json()["game_id"]
        for mark, cell in [("X", 0), ("O", 1), ("X", 4), ("O", 2), ("X", 8)]:
            client.post(f"/api/v1/games/{gid_finished}/moves", json={"mark": mark, "cell": cell})
        r_in_progress = client.get("/api/v1/games?status=in_progress")
        r_finished = client.get("/api/v1/games?status=finished")
        assert r_in_progress.json()["total"] == 1
        assert r_finished.json()["total"] == 1
    finally:
        teardown_db(db)


def test_list_games_pagination():
    client, db = get_client()
    try:
        for _ in range(5):
            client.post("/api/v1/games", json={"mode": "hotseat", "player_x_id": 1, "player_o_id": 1})
        r1 = client.get("/api/v1/games?page=1&page_size=2")
        r2 = client.get("/api/v1/games?page=2&page_size=2")
        assert r1.json()["total"] == 5
        assert len(r1.json()["items"]) == 2
        assert len(r2.json()["items"]) == 2
    finally:
        teardown_db(db)
