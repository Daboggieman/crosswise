CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    kind TEXT NOT NULL
        CHECK (kind IN ('human', 'bot')),
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE games (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL
        CHECK (mode IN ('hotseat', 'vs_bot', 'online')),
    status TEXT NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'finished', 'abandoned')),

    player_x_id INTEGER NOT NULL
        REFERENCES players(id),
    player_o_id INTEGER NOT NULL
        REFERENCES players(id),

    winner TEXT,
    result_reason TEXT,
    move_count INTEGER NOT NULL DEFAULT 0,
    summary_text TEXT,
    engine_version TEXT NOT NULL,

    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP
);

CREATE TABLE moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL
        REFERENCES games(id) ON DELETE CASCADE,

    seq INTEGER NOT NULL,
    ply INTEGER NOT NULL,
    mark TEXT NOT NULL,
    cell INTEGER NOT NULL,
    played_at TIMESTAMP NOT NULL,

    UNIQUE (game_id, ply),
    UNIQUE (game_id, seq),
    UNIQUE (game_id, cell),

    CHECK (cell BETWEEN 0 AND 8),
    CHECK (mark IN ('X', 'O'))
);

CREATE TABLE actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL
        REFERENCES games(id) ON DELETE CASCADE,

    seq INTEGER NOT NULL,
    type TEXT NOT NULL
        CHECK (
            type IN (
                'resign',
                'offer_draw',
                'accept_draw',
                'decline_draw',
                'timeout',
                'disconnect',
                'reconnect'
            )
        ),

    actor TEXT NOT NULL
        CHECK (actor IN ('X', 'O', 'system')),

    payload TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE search_index_state (
    game_id TEXT PRIMARY KEY
        REFERENCES games(id) ON DELETE CASCADE,

    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'indexed', 'failed')),

    last_error TEXT,
    indexed_at TIMESTAMP
);

CREATE INDEX idx_games_status
    ON games(status);

CREATE INDEX idx_games_started_at
    ON games(started_at DESC);

CREATE INDEX idx_games_winner
    ON games(winner);

CREATE INDEX idx_actions_game_id_seq
    ON actions(game_id, seq);

CREATE INDEX idx_search_index_state_status
    ON search_index_state(status);