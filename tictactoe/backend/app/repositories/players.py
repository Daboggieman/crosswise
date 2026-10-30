def get_by_name(connection, display_name):
    cursor = connection.execute(
        """
        SELECT id, display_name, kind, created_at
        FROM players
        WHERE display_name = ?
        """,
        (display_name,),
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "kind": row["kind"],
        "created_at": row["created_at"],
    }

def create(connection, display_name, kind, now):
    row = connection.execute(
        """
        INSERT INTO players (
        display_name,
        kind,
        now
        ) VALUES (?, ?, ?)
        """,
        (display_name,
        "Human",
        now.isoformat(),
        )
    )
    return row.lastrowid
