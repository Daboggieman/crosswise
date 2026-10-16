import sqlite3
from pathlib import Path
from app.db.connection import connect

def run_migrations(settings) -> int:
    """Apply unapplied SQL migrations in order and return the count."""
    database_path = Path(settings.database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    migrations_dir = Path(settings.migrations_dir)
    connection = connect(settings)
    applied_count = 0

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
        rows = connection.execute(
            "SELECT name FROM schema_migrations"
        ).fetchall()
        applied = {row["name"] for row in rows}
        migration_files = sorted(
            path
            for path in migrations_dir.iterdir()
            if path.is_file() and path.suffix == ".sql"
        )
        for migration_file in migration_files:
            migration_name = migration_file.name
            if migration_name in applied:
                continue
            sql = migration_file.read_text(encoding="utf-8")
            try:
                connection.executescript(
                    "BEGIN IMMEDIATE;\n" + sql
                )

                connection.execute(
                    """
                    INSERT INTO schema_migrations (name)
                    VALUES (?)
                    """,
                    (migration_name,),
                )

                connection.commit()

            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            applied.add(migration_name)
            applied_count += 1

        print(f"Applied {applied_count} migration(s).")
        return applied_count

    finally:
        connection.close()