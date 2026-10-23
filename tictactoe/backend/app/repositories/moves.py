def insert(connection, game_id, seq, ply, mark, cell, played_at):
    connection.execute(
        """
        INSERT INTO moves (
        game_id, 
        seq, 
        ply, 
        mark, 
        cell, 
        played_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, 
        (game_id, 
        seq, 
        ply, 
        mark, 
        cell, 
        played_at)
    )

def list_for_game(connection, game_id):
    rows = connection.execute(
        """
        SELECT * FROM moves WHERE game_id = ? ORDER BY seq ASC
        """,
        (game_id,),
    ).fetchall()
    return [dict(row) for row in rows]

def count_for_game(connection, game_id):
    rows = connection.execute(
        """
        SELECT COUNT(*) as count FROM moves WHERE game_id = ?
        """,
        (game_id,),
    ).fetchall()
    return rows[0]['count']