import sqlite3
from contextlib import contextmanager

def connect(settings):
    connection = sqlite3.connect(
        settings.database_path,
        check_same_thread=False,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection

@contextmanager
def transaction(settings, immediate=False):
    connection = connect(settings)
    try:
        connection.execute(
            "BEGIN IMMEDIATE" if immediate else "BEGIN"
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()