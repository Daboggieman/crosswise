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
