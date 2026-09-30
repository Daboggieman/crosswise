# Tic Tac Toe Platform: Technical Build Docs

Version 1.0. This is a specification and build plan only. It contains no implementation code, so every line of the actual system is yours to write.

---

## 0. How to Use These Docs

**Ground rules (your own)**

- No AI-written code. Books, official docs, and web searches are allowed for small problems.
- Write the code, tests, and migrations yourself. Use this document as the blueprint.

**Verification checkpoints** Every build phase in Section 14 starts with a **Verify first** block: a short list of things to confirm are already true before you start that phase's tasks. Do not skip it. If a check fails, fix the previous phase first.

**Decisions** Items marked **\[Decision\]** are recommendations. Change them if you have a reason, then update this document so it stays accurate.

---

## 1. Scope

### 1.1 Goals

1. A correct, well-tested tic tac toe engine in Python.
2. A backend that exposes the engine over an API and persists everything.
3. A frontend where a person can play a game.
4. A database that stores games, moves, and actions.
5. Semantic search over saved games using your own search engine.
6. Replay of any saved game, including games found through search.

### 1.2 Non-goals for v1

- Accounts with passwords, OAuth, or payments.
- Boards larger than 3x3 or variants (Ultimate, Misere).
- Mobile apps.
- Horizontal scaling.

### 1.3 Play modes

| Mode | Description | Phase |
| --- | --- | --- |
| Hotseat | Two humans, one browser | 3 |
| Vs bot | Human against a computer opponent | 6 |
| Online 1v1 | Two browsers, real time | 9 (stretch) |

---

## 2. Architecture

### 2.1 Layers

```
 Frontend (browser)
     |  HTTP/JSON (later: WebSocket)
 API layer (routing, validation, serialization)
     |
 Service layer (game flow, search orchestration, replay assembly)
     |             |
 Engine        Repository layer          Search adapter
 (pure logic)  (all SQL lives here)      (your semantic engine)
                   |
               Database
```

### 2.2 Rules that keep it clean

1. **The engine is pure.** No database, no HTTP, no clock, no randomness inside the rules. Same input, same output, always.
2. **Only the repository layer talks to the database.** Nothing else imports the database driver.
3. **Only the search adapter talks to your search engine.** If its interface changes, one module changes.
4. **The API layer holds no game rules.** It validates shape, calls a service, and formats the result.
5. **The move log is the source of truth.** The board you show is always derivable by replaying stored moves.

---

## 3. Tech Stack

| Concern | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.12+ |  |
| Web framework | FastAPI **\[Decision\]** | Alternative: Flask. FastAPI gives typed request validation and auto-generated API docs. |
| Server | Uvicorn |  |
| Database | SQLite for dev, PostgreSQL later **\[Decision\]** | Keep SQL portable so the swap is a config change. |
| DB access | Plain SQL through the standard driver, or SQLAlchemy Core **\[Decision\]** | Plain SQL teaches the most and fits the no-AI spirit. |
| Migrations | Numbered SQL files applied in order | Simple, transparent. Alembic if you move to SQLAlchemy. |
| Frontend | Plain HTML, CSS, and JavaScript **\[Decision\]** | No framework needed for this size. Add one only if state gets painful. |
| Tests | pytest |  |
| Config | Environment variables | One settings module reads them. |

---

## 4. Repository Layout

```
tictactoe/
  docs/                 this document, decisions log
  backend/
    app/
      main              app creation and wiring
      config            settings from environment
      api/              routers, request/response schemas, error handlers
      services/         game_service, search_service, replay_service
      engine/           board, rules, notation, bot
      repositories/     games, moves, actions, search_state
      search/           adapter to your semantic search engine
      db/               connection handling, migration runner
    migrations/         0001_..., 0002_... numbered SQL files
    tests/
      unit/             engine and pure functions
      integration/      repository and API against a test database
  frontend/
    index, play, history, replay pages
    js/                 api client, board view, replay controller, search view
    css/
  scripts/              seed data, reindex, integrity check
```

---

## 5. Engine Specification

### 5.1 Board representation

- Nine cells, indexed 0 to 8, row-major:

```
 0 | 1 | 2
---+---+---
 3 | 4 | 5
---+---+---
 6 | 7 | 8
```

- Each cell is empty, X, or O.
- X always moves first.

### 5.2 Game state

A state consists of:

- the board (nine cells)
- whose turn it is
- status: in progress, won, or drawn
- winner (X, O, or none)
- the winning line, if any (useful for highlighting in the UI and for search summaries)

States are **immutable**. Applying a move returns a new state and never modifies the old one. This makes replay and testing trivial.

### 5.3 Winning lines

Eight lines: three rows, three columns, two diagonals. Define them once as constants.

### 5.4 Operations the engine must provide

| Operation | Behavior |
| --- | --- |
| New game | Returns an empty board, X to move, in progress |
| Legal moves | Returns the empty cells, or nothing if the game is over |
| Apply move | Takes a state, a player, and a cell. Returns the new state, or raises a specific error |
| Evaluate | Determines won, drawn, or in progress for a given board |
| Replay | Folds a list of cells over a new game and returns the final state |

### 5.5 Error types

Define distinct errors so the API can map them to responses:

- cell out of range
- cell already occupied
- not this player's turn
- game already finished

### 5.6 Invariants (write these as tests)

1. Count of X equals count of O, or exceeds it by exactly one.
2. Once won or drawn, no further move is accepted.
3. A win is detected on the exact move that completes a line, not one move late.
4. A full board with no line is a draw, and a full board where the last move completes a line is a win, not a draw.
5. Replaying a game's move list always reproduces its stored final result.

### 5.7 Notation

Store moves as the cell index (0 to 8). For human-readable output define a coordinate form (for example row and column, or A1 to C3) in one place only, and convert at the edges.

### 5.8 Bot (Phase 6)

- **Easy:** random legal move.
- **Medium:** win if possible, else block, else random.
- **Hard:** exhaustive game-tree search (minimax). The full tree is small, so it is solvable exactly. Add pruning as an optional optimization exercise.
- The bot lives in the engine package, receives a state, and returns a cell. It must be deterministic for a given seed so bot games are reproducible in tests.

---

## 6. Database Design

### 6.1 Tables

**players**

| Column | Type | Notes |
| --- | --- | --- |
| id | integer or UUID, primary key |  |
| display_name | text, not null |  |
| kind | text, not null | human or bot |
| created_at | timestamp, not null |  |

Include a fixed set of bot players (easy, medium, hard) created by a migration.

**games**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID, primary key |  |
| mode | text, not null | hotseat, vs_bot, online |
| status | text, not null | in_progress, finished, abandoned |
| player_x_id | foreign key to players |  |
| player_o_id | foreign key to players |  |
| winner | text, nullable | X, O, or null for draw or unfinished |
| result_reason | text, nullable | three_in_row, draw, resignation, timeout, agreement |
| move_count | integer, not null, default 0 | Denormalized for fast listing |
| summary_text | text, nullable | Generated description used for search (see Section 9) |
| engine_version | text, not null | So old games stay replayable if rules ever change |
| started_at | timestamp, not null |  |
| ended_at | timestamp, nullable |  |

**moves**

| Column | Type | Notes |
| --- | --- | --- |
| id | integer, primary key |  |
| game_id | foreign key to games, on delete cascade |  |
| ply | integer, not null | 1-based move number |
| mark | text, not null | X or O |
| cell | integer, not null | 0 to 8 |
| played_at | timestamp, not null |  |

Constraints:

- unique on (game_id, ply)
- unique on (game_id, cell), because a cell can only be played once per game
- check that cell is between 0 and 8
- check that mark is X or O

**actions** Non-move events that still matter for history and replay.

| Column | Type | Notes |
| --- | --- | --- |
| id | integer, primary key |  |
| game_id | foreign key to games, on delete cascade |  |
| seq | integer, not null | Ordering within the game across moves and actions |
| type | text, not null | resign, offer_draw, accept_draw, decline_draw, timeout, disconnect, reconnect |
| actor | text, not null | X, O, or system |
| payload | text (JSON), nullable | Extra detail, such as time remaining |
| created_at | timestamp, not null |  |

**search_index_state**

| Column | Type | Notes |
| --- | --- | --- |
| game_id | primary key, foreign key to games |  |
| content_hash | text | Hash of the indexed text, to detect changes |
| status | text | pending, indexed, failed |
| last_error | text, nullable |  |
| indexed_at | timestamp, nullable |  |

### 6.2 Ordering across moves and actions

A replay needs one timeline. Two options:

- **Option A \[Decision\]:** give moves and actions a shared `seq` per game. Add `seq` to moves too, and keep `ply` for the pure move count.
- **Option B:** merge by timestamp at read time. Simpler schema, but ties and clock skew are a risk.

Option A is safer. If you choose it, add `seq` to the moves table with a unique constraint on (game_id, seq), and make sure seq is allocated inside the same transaction as the insert.

### 6.3 Indexes

- games: (status), (started_at descending), (winner)
- moves: covered by the unique constraints
- actions: (game_id, seq)
- search_index_state: (status)

### 6.4 Transactions

Playing a move must, in one transaction: verify the game is in progress, verify turn order, insert the move, update move_count, and if the move ends the game, update status, winner, result_reason, and ended_at. Either all of it commits or none of it does.

### 6.5 Concurrency

Two requests could try to play the same ply at once. The unique constraint on (game_id, ply) is your safety net. Catch that constraint violation and return a conflict error rather than a server error.

### 6.6 Migrations

- Numbered files applied in order.
- A table records which migrations have run.
- Never edit an applied migration. Add a new one.

---

## 7. API Specification

Base path: `/api/v1`. All bodies are JSON. Timestamps are ISO 8601 in UTC.

### 7.1 Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | Liveness check |
| POST | /games | Create a game |
| GET | /games | List games with filters and pagination |
| GET | /games/{id} | Get one game with its current board |
| POST | /games/{id}/moves | Play a move |
| POST | /games/{id}/actions | Resign, offer or answer a draw, and so on |
| GET | /games/{id}/replay | Get the ordered timeline for replay |
| POST | /search | Semantic search over games |
| POST | /admin/reindex | Rebuild search index (protect or disable outside dev) |

### 7.2 Request and response shapes

**Create game**

- Request: mode, player X, player O (or bot difficulty).
- Response: game id, mode, status, empty board, next player.

**Play move**

- Request: mark, cell.
- Response: updated board, next player, status, winner, winning line, move number. For vs-bot games, include the bot's reply move in the same response.

**Get game**

- Response: game metadata plus a board array of nine values, the list of moves, and the list of actions.

**List games**

- Query params: status, winner, mode, player, date range, page, page size, sort.
- Response: items, total, page info.

**Replay**

- Response: game metadata and one ordered `timeline` array. Each entry has seq, kind (move or action), and its details. Include the final result for verification.

**Search**

- Request: query text, optional filters (same as list), limit, minimum score.
- Response: ordered results, each with game id, relevance score, the matched summary text, and enough metadata to show a result card. Include the game id so the UI can link straight to replay.

### 7.3 Error format

One consistent shape for every error: a machine-readable code, a human message, and optional details.

| Situation | Status | Code |
| --- | --- | --- |
| Malformed body or out-of-range cell | 422 | validation_error |
| Game not found | 404 | game_not_found |
| Cell occupied, not your turn, game finished, stale ply | 409 | illegal_move or conflict |
| Search engine unreachable | 503 | search_unavailable |
| Anything unexpected | 500 | internal_error (never leak internals) |

### 7.4 Idempotency

Include a client-supplied ply or move number in the play-move request. If the same request is retried, the server can detect it and return the existing result instead of double-applying.

---

## 8. Actions Model

| Action | Effect |
| --- | --- |
| resign | Game finishes, opponent wins, reason is resignation |
| offer_draw | Recorded, waits for a response |
| accept_draw | Game finishes as draw, reason is agreement |
| decline_draw | Recorded, game continues |
| timeout | System-generated, game finishes, reason is timeout |
| disconnect and reconnect | Recorded for online mode only |

Rules:

- Every action is validated against current game state (you cannot accept a draw nobody offered).
- Every action gets a seq in the shared timeline.
- Actions that end a game go through the same transactional path as a winning move.

---

## 9. Semantic Search Integration

Your search engine is a black box to this project except for the contract below. **Confirm the real contract before Phase 7** (see open questions, Section 16).

### 9.1 What gets indexed

Raw move lists mean little to a semantic engine. Index a **generated description** for each finished game, stored in `games.summary_text`. Generate it with a deterministic template, not a model.

Facts a description can include:

- who won or that it was a draw, and how many moves it took
- which line won (top row, main diagonal, and so on)
- who opened and where (center, corner, edge)
- notable patterns: won by a fork, opponent failed to block, early win, full-board draw
- mode and bot difficulty
- date

Example description (illustrative only): "X won in 5 moves along the main diagonal. X opened in the center against the hard bot. The bot's second move missed a block."

Detecting patterns like a missed block means the engine or a helper needs an analysis function that walks the move list. That is a good self-contained exercise.

### 9.2 Indexing pipeline

1. When a game finishes, insert or update its `search_index_state` as pending.
2. A background step (a simple worker, or a post-commit call at first) builds the description, saves it, computes a content hash, and sends it to the search engine.
3. On success mark indexed. On failure mark failed and store the error.
4. A script retries failed and pending rows.
5. A full reindex script rebuilds everything, so you can change the description template freely.

**Important:** never let a search outage block or fail a game. Indexing is best-effort and retryable.

### 9.3 Query flow

1. Client sends a text query and optional filters.
2. Search service calls the adapter with the query.
3. Adapter returns game ids with scores.
4. Search service loads those games from the database (one query, not one per result), applies any structured filters, and preserves score order.
5. Response combines the score, the description, and game metadata.

### 9.4 Adapter contract (draft, adjust to your engine)

- **index(document id, text, metadata)**: add or update.
- **delete(document id)**.
- **search(query, limit, filters)**: returns a list of (document id, score).
- **health()**: reachable or not.

Keep this as a small interface with your real client behind it, plus a fake in-memory implementation for tests.

### 9.5 Hybrid filtering

Decide early whether filters (winner, mode, date) run inside your search engine or after retrieval in SQL. Filtering after retrieval is simpler but can return fewer results than the limit. Overfetch (for example ask for 3x the limit) to compensate, or push filters into the engine.

---

## 10. Replay

### 10.1 Data source

The `replay` endpoint returns the ordered timeline from Section 6.2. The frontend never calls the engine. It receives cells and marks and draws them.

### 10.2 Server-side verification

When assembling a replay, the replay service folds the moves through the engine and compares the outcome to the stored winner and result. If they differ, flag the game as inconsistent in the response and in logs. This catches data corruption and engine changes.

### 10.3 Frontend replay controller

State: the timeline, a current step index, playing or paused, speed.

Controls: play, pause, step forward, step back, jump to start, jump to end, seek to a specific step, speed selector.

Behavior:

- The board at step N is computed by applying the first N moves. Do this from scratch on each seek, so seeking is always correct.
- Actions appear as annotations on the timeline (for example "X offered a draw").
- The last step shows the result and highlights the winning line.
- Optional: keyboard shortcuts (left, right, space).

### 10.4 Entry points

- From the history list.
- From a search result.
- Via a shareable URL that contains only the game id.

---

## 11. Frontend Specification

### 11.1 Pages

| Page | Contents |
| --- | --- |
| Play | Mode selection, board, turn indicator, status, resign and draw buttons, new game |
| History | Filterable, paginated list of past games |
| Search | Text box, filters, result cards with a Replay button |
| Replay | Board, timeline, controls, game metadata |

### 11.2 Modules (plain JavaScript)

- **API client:** one place for all fetch calls and error handling.
- **Board view:** renders nine cells from an array, emits click events, highlights a winning line.
- **Game controller:** holds current game state, calls the API, updates the view.
- **Replay controller:** Section 10.3.
- **Search view:** query, results, empty and error states.

### 11.3 UX requirements

- Disable the board when it is not the player's turn or the game is over.
- Show clear messages for illegal moves rather than failing silently.
- Show loading and error states for every network call.
- Keyboard accessible cells with proper labels.
- Works at phone width.

### 11.4 Rule

The frontend may pre-check obvious things for responsiveness, but the server is the only authority on legality.

---

## 12. Testing Strategy

### 12.1 Engine unit tests (most important)

- Every winning line, for both players.
- Draw detection on a full board.
- A win on the ninth move counts as a win.
- Every error type.
- Immutability: the old state is unchanged after applying a move.
- Exhaustive check: generate every reachable game and assert all invariants hold. The full space is small enough to walk completely.
- Bot: hard bot never loses against any opponent line of play.

### 12.2 Repository tests

- Run against a real temporary database.
- Constraint tests: duplicate ply, duplicate cell, out-of-range cell, bad mark.
- Transaction test: a failure midway leaves no partial data.

### 12.3 API tests

- Full game to a win, to a draw, to a resignation.
- Every error path and its status code.
- Retried request does not double-apply.
- Pagination and filters.

### 12.4 Search tests

- Use the fake adapter for logic.
- A small number of tests against the real engine, marked separately.
- Outage test: search down, games still play and finish.

### 12.5 Replay tests

- Replay of every stored game reproduces its result.
- Corrupted data is flagged.

### 12.6 Target

High coverage on engine and services. Do not chase a number on the API glue.

---

## 13. Non-Functional Requirements

- **Config:** database location, search engine address, log level, and allowed origins all come from environment variables, with safe defaults for development.
- **Logging:** structured, one line per request, with a request id. Log every rejected move at info level.
- **Validation:** validate at the API boundary and again in the engine. Never trust the client.
- **Security basics:** parameterized queries only, restrict CORS, protect admin routes, cap request size, cap page size.
- **Performance:** listing must not run one query per row. Add the indexes from Section 6.3.
- **Time:** always store UTC. Pass the clock in from outside so time is testable.
- **Observability:** the health endpoint should also report database and search engine reachability.

---

## 14. Build Phases

Each phase has: **Verify first** (confirm the previous phase truly works), **Tasks**, and **Done when**.

### Phase 0: Setup

**Verify first:** nothing yet. Confirm you have Python 3.12+ and Git.

Tasks

- Create the repo and layout from Section 4.
- Set up a virtual environment and dependency file.
- Configure pytest with one trivial passing test.
- Set up formatting and linting.

Done when: the test suite runs from a clean checkout in one command.

### Phase 1: Engine

**Verify first:** the test runner works and the package imports.

Tasks

- Board, state, winning lines, apply move, evaluate, replay.
- Error types.
- All invariants from Section 5.6 as tests.
- Exhaustive game-space test.

Done when: engine tests pass and you can play a complete game in a Python shell.

### Phase 2: Database and repositories

**Verify first:** run the engine suite again. Confirm you can create a game in a shell with no database involved.

Tasks

- Migration runner and migrations 0001 onward for all tables.
- Repositories for games, moves, actions.
- Transactional play-move operation.
- Constraint and transaction tests.

Done when: you can play a full game in a shell and the rows appear correctly in the database, and the replayed result matches.

### Phase 3: API and hotseat frontend

**Verify first:** confirm from a shell that a game persists, reloads, and replays to the same result.

Tasks

- App wiring, config, error handlers.
- Create, get, list, move, action endpoints.
- Play page with hotseat mode.
- API tests.

Done when: two people can finish a game in the browser and it shows in the database.

### Phase 4: History and replay

**Verify first:** confirm that a finished game exists in the database and the get-game endpoint returns its moves in order.

Tasks

- Replay endpoint with server-side verification.
- History page with filters and pagination.
- Replay page and controller.

Done when: every stored game replays correctly, and seeking to any step shows the right board.

### Phase 5: Actions

**Verify first:** confirm the shared timeline ordering works (moves and actions interleave correctly in a replay).

Tasks

- Resign, draw offer flow, timeout.
- Show actions on the replay timeline.

Done when: each ending type produces the correct stored result and replays correctly.

### Phase 6: Bot

**Verify first:** confirm a full human game still works end to end after Phase 5.

Tasks

- Easy, medium, hard bots.
- Vs-bot mode returning the bot reply.
- Seeded determinism.

Done when: hard bot never loses in tests, and bot games are stored and replayable like any other.

### Phase 7: Search

**Verify first:** confirm your search engine is running and you have its real interface in hand. Confirm at least several dozen finished games exist (seed some with a script driven by the bot).

Tasks

- Description generator and pattern analysis.
- Adapter, fake adapter, indexing state and retry script.
- Search endpoint and search page.
- Reindex script.

Done when: a natural-language query returns sensible games and each result opens its replay.

### Phase 8: Hardening

**Verify first:** run the full test suite and confirm it is green.

Tasks

- Integrity-check script that replays every game and reports mismatches.
- Logging, config review, security review.
- Concurrency test for duplicate ply.
- Documentation of how to run everything.

Done when: a new machine can run the project from the README alone.

### Phase 9 (stretch): Online 1v1

**Verify first:** confirm vs-bot and hotseat still work.

Tasks

- WebSocket channel per game.
- Server pushes moves and actions to both players.
- Player identity per connection.
- Disconnect and reconnect handling, timeouts.

Done when: two browsers can finish a game in real time.

---

## 15. Reading List

Use these when stuck, in the pre-AI spirit.

- Python official documentation (standard library, typing, sqlite3, unittest).
- FastAPI official documentation, or Flask's if you go that route.
- SQLite documentation on constraints, transactions, and indexes.
- MDN Web Docs for DOM, fetch, and accessibility.
- *Fluent Python* by Luciano Ramalho, for idiomatic Python.
- *Architecture Patterns with Python* by Percival and Gregory, for the repository and service layer ideas used here.
- *Designing Data-Intensive Applications* by Martin Kleppmann, chapters on transactions and data models.
- *SQL Antipatterns* by Bill Karwin.
- Any introductory chapter on game-tree search and minimax, for the hard bot.

---

## 16. Open Questions

Answer these and record the answers in your decisions log.

1. What is your search engine's real interface (HTTP, Python library, CLI)? What does it return, and does it support metadata filters?
2. Should search index only finished games, or in-progress too?
3. Do you want player accounts in v1, or only named players and bots?
4. SQLite only, or PostgreSQL from the start?
5. Is online 1v1 a real goal or just a maybe?
6. Should replays be shareable publicly, or private to a player?

---

## 17. Definition of Done (whole project)

- All engine invariants and exhaustive tests pass.
- Every stored game replays to its recorded result.
- A game can be played in hotseat and against each bot.
- A natural-language search returns relevant games, and each result opens a working replay.
- Search outage does not break gameplay.
- The project runs from a fresh checkout using only the README.