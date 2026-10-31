"""Integration tests for the players repository and player_service (spec 6.1, 7.2).

Covers the name-based player resolution added for the hotseat frontend:
create persists a human row, repeated names reuse the existing row, names are
trimmed, and blank names are rejected without leaving a row behind.
"""
from datetime import UTC, datetime

import pytest

from app.db.connection import connect, transaction
from app.repositories import players
from app.services.player_service import PlayerValidationError, get_or_create_player


def now():
    return datetime.now(UTC)


def count_players(settings, display_name=None):
    conn = connect(settings)
    try:
        if display_name is None:
            return conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        return conn.execute(
            "SELECT COUNT(*) FROM players WHERE display_name = ?", (display_name,)
        ).fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# players repository
# ---------------------------------------------------------------------------

def test_create_inserts_human_player(settings):
    with transaction(settings, immediate=True) as tx:
        pid = players.create(tx, "Ada", "human", now())
    conn = connect(settings)
    try:
        row = players.get_by_name(conn, "Ada")
    finally:
        conn.close()
    assert row is not None
    assert row["id"] == pid
    assert row["display_name"] == "Ada"
    assert row["kind"] == "human"


def test_get_by_name_missing_returns_none(settings):
    conn = connect(settings)
    try:
        assert players.get_by_name(conn, "Nobody") is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# get_or_create_player (service)
# ---------------------------------------------------------------------------

def test_get_or_create_creates_then_reuses(settings):
    pid1 = get_or_create_player(settings, "Ada")
    assert isinstance(pid1, int)
    assert count_players(settings, "Ada") == 1

    pid2 = get_or_create_player(settings, "Ada")
    assert pid2 == pid1
    assert count_players(settings, "Ada") == 1

    conn = connect(settings)
    try:
        row = players.get_by_name(conn, "Ada")
    finally:
        conn.close()
    assert row["kind"] == "human"


def test_get_or_create_trims_whitespace(settings):
    pid1 = get_or_create_player(settings, "  Ada  ")
    conn = connect(settings)
    try:
        row = players.get_by_name(conn, "Ada")
    finally:
        conn.close()
    assert row is not None
    assert row["display_name"] == "Ada"
    assert get_or_create_player(settings, "Ada") == pid1


def test_get_or_create_rejects_blank_names(settings):
    before = count_players(settings)
    for blank in ("", "   "):
        with pytest.raises(PlayerValidationError):
            get_or_create_player(settings, blank)
    assert count_players(settings) == before
