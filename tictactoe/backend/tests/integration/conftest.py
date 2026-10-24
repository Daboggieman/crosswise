"""Shared fixtures for integration tests: a real temporary database."""
import os
import sys
import uuid
from pathlib import Path

import pytest

# Make `app` importable regardless of where pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.db.migration_runner import run_migrations


@pytest.fixture()
def settings(tmp_path):
    """Settings pointing at a fresh temporary database per test."""
    os.environ["DATABASE_URL"] = f"/tmp/crosswise-test-{uuid.uuid4().hex}.db"
    os.environ["MIGRATIONS_DIR"] = str(BACKEND_DIR / "migrations")
    s = get_settings()
    run_migrations(s)
    yield s
    # Cleanup: remove the database files.
    db_path = Path(s.database_path)
    for suffix in ("", "-wal", "-shm"):
        f = Path(str(db_path) + suffix)
        if f.exists():
            f.unlink()
