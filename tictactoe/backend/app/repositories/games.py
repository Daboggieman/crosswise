"""

all SQL touching the games table lives here, and nowhere else
(spec rule: only the repository layer talks to the database).
Every function takes a connection as an argument — the repository never opens connections itself; 
the caller (service or test) brings one, usually from transaction(). 
That's what makes the same repository code usable inside and outside a transaction

"""
import uuid


def create(connection, mode, player_x_id, player_o_id, engine_version, now):
    game_id = str(uuid.uuid4())
    started_at = now.isoformat()

    connection.execute(
        """
        INSERT INTO games (
            id, mode, player_x_id, player_o_id, engine_version, started_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (game_id, 
        mode, 
        player_x_id,
        player_o_id,
        engine_version,
        started_at,
        ),
    )
    return game_id

def get_game(connection, game_id):
    row = connection.execute(
        """
        SELECT * FROM games WHERE id = ?
        """,
        (game_id,),
    ).fetchone()
    return dict(row) if row else None


MAX_PAGE_SIZE = 100


def list_games(connection, filters=None):
    if filters is None:
        filters = {}
    clauses = ["SELECT id, mode, player_x_id, player_o_id, engine_version, started_at, status, winner, move_count FROM games"]
    params = []
    where_clauses =[]

    if filters.get("status") is not None:
        where_clauses.append("status = ?")
        params.append(filters["status"])
    
    if filters.get("winner") is not None:
        where_clauses.append("winner = ?")
        params.append(filters["winner"])
    
    if filters.get("mode") is not None:
        where_clauses.append("mode = ?")
        params.append(filters["mode"])
    
    if filters.get("player") is not None:
        where_clauses.append("(player_x_id = ? OR player_o_id = ?)")
        params.extend([filters["player"], filters["player"]])
    
    if filters.get("started_after") is not None:
        where_clauses.append("started_at >= ?")
        params.append(filters["started_after"])
    
    if filters.get("started_before") is not None:
        where_clauses.append("started_at <= ?")
        params.append(filters["started_before"])

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)
    sort_options = {
        "started_at_desc": "started_at DESC",
        "started_at_asc": "started_at ASC",
        "move_count_desc": "move_count DESC",
        "move_count_asc": "move_count ASC",
    }

    sort_key = filters.get("sort", "started_at_desc")
    order_sql = sort_options.get(sort_key, "started_at DESC")

    page = max(1, filters.get("page", 1))
    page_size = max(1, min(filters.get("page_size", 25), MAX_PAGE_SIZE))
    limit = page_size

    query = (
        clauses[0]
        + where_sql
        + f"ORDER BY {order_sql} LIMIT ? OFFSET ?"
    )
    offset = (page - 1) * page_size
    query_params = params + [limit, offset]
    rows = connection.execute(query, query_params).fetchall()
    
    count_query = "SELECT COUNT(*) FROM games" + where_sql
    total = connection.execute(count_query, params).fetchone()[0]
    
    return {
        "games": rows,
        "total": total,
    }

def update_result(connection, game_id, status, winner, result_reason, ended_at):
    connection.execute(
        """UPDATE games
        SET status = ?, winner = ?, result_reason = ?, ended_at = ? 
        WHERE id = ?
        """,(status, winner, result_reason, ended_at, game_id)
    )

def increment_move_count(connection, game_id):
    connection.execute(
        """
        UPDATE games
        SET move_count = move_count + 1
        WHERE id = ?
        """, (game_id,)
    )