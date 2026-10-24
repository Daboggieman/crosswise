def insert(connection, game_id, seq, type, actor, payload, created_at):
    connection.execute(
        """
        INSERT INTO actions(
            game_id, 
            seq, 
            type, 
            actor, 
            payload, 
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
        game_id, 
        seq, 
        type, 
        actor, 
        payload, 
        created_at
        )
    )

def list_for_game(connection, game_id):
    rows = connection.execute(
        """
        SELECT * FROM actions WHERE game_id = ? ORDER BY seq ASC
        """,
        (game_id,),
    ).fetchall()
    return [dict(row) for row in rows]

def count_for_game(connection, game_id):
    row = connection.execute(
        """
        SELECT COUNT(*) AS count FROM actions WHERE game_id = ?
        """,
        (game_id,),
    ).fetchone()
    return row["count"]

def max_seq_for_game(connection, game_id):
    """Highest seq used by any action in this game, or 0 if there are none."""
    row = connection.execute(
        """
        SELECT COALESCE(MAX(seq), 0) AS max_seq FROM actions WHERE game_id = ?
        """,
        (game_id,),
    ).fetchone()
    return row["max_seq"]
