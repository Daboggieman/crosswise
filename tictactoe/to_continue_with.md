# To Continue With — Crosswise Tic Tac Toe

State of the project as of 2026-10-24, and what comes next.
Spec reference: `Tic Tac Toe Platform_ Technical Build Docs.md` in this folder.

---

## Where things stand

### Phase 2 — Database and repositories: DONE ✅

- Migrations 0001/0002, migration runner, all three repositories, transactional
  `play_move` in `app/services/game_service.py`.
- 55 tests covering engine, repositories, constraints, rollback, and the service.
- Shared-seq allocation fixed to use `MAX(seq)` (was `COUNT(*)`, which collided
  when an action interleaved between moves).

### Phase 3 — API: backend DONE, frontend NOT STARTED

Backend complete and green (**72 tests pass, ruff clean**):

- `app/api/schemas.py` — Pydantic request/response models
- `app/api/errors.py` — app-wide handlers mapping service exceptions to
  404/422/409 with the spec §7.3 shape (`code`, `message`, `details`)
- `app/api/routes_games.py` — create / list / get / play-move endpoints
- `app/main.py` — `create_app()` with CORS, router under `/api/v1`,
  `GET /api/v1/health`
- `tests/integration/test_api.py` — 17 API tests (spec §12.3)

Run the server from `tictactoe/backend/`:

```
.venv/bin/python -m uvicorn app.main:app --reload
```

### Remaining for Phase 3 — the hotseat frontend (needs pseudocode first)

- `frontend/` directory per spec §4: `index`, `play`, `history`, `replay` pages,
  plus `js/` (api client, board view, game controller) and `css/`.
- For Phase 3 only the **Play page with hotseat mode** is required
  (history/replay/search pages come later).
- UX rules from spec §11.3: disable board when not your turn or game over,
  clear illegal-move messages, loading/error states, keyboard-accessible cells,
  works at phone width.
- **Serve it from FastAPI** (no separate server needed): mount static files in
  `create_app()` and serve `play.html` at a route, or use plain
  `StaticFiles(directory="frontend")`. Decide before writing the frontend.

---

## Known gaps / decisions to record (from Phase 3)

1. **Idempotency (spec §7.4) is not implemented.** `PlayMoveRequest` carries a
   `ply` field, but `game_service.play_move` ignores it — retries are currently
   only protected by the occupied-cell constraint (a retried same-cell request
   gets 422, not the original result). Implementing true ply-based retry
   detection is a small service change; pseudocode available on request.
2. **Occupied cell returns 422, spec §7.3 suggests 409.** The service raises
   `GameValidationError` for occupied cells. Current split: bad input (bad
   cell range, bad mark, occupied) → 422; state conflicts (wrong turn, game
   over) → 409. Defensible, but record the decision in the decisions log.
3. **Status vocabulary:** the engine says `won`/`drawn`, the DB stores
   `finished`. The API maps engine → DB status in play-move responses and
   returns DB status in get/list responses. Tests pin this behavior — keep it
   consistent when adding endpoints.
4. **`ActionOut.payload`** is `dict | None` — actions currently always have
   `NULL` payload since the actions endpoint doesn't exist yet (Phase 5).
5. **`httpx` was installed** into `.venv` (test-only dep, needed for the API
   tests). Starlette warns `httpx2` is preferred; harmless for now.

## Housekeeping

- A stray `tictactoe.db` (and possibly `-wal`/`-shm`) sits in the backend
  directory from smoke tests — delete it or add `*.db` / `tictactoe.db*` to
  `.gitignore` before it gets committed by accident.
- `requirements.txt` should gain `httpx` (dev/test only) so a clean checkout
  can run the API tests.
- `.pytest_cache/` and `__pycache__/` should be gitignored if not already.

## Next phases (spec §14)

- **Phase 4 — History and replay.** Verify first: a finished game exists and
  `GET /games/{id}` returns its moves in order (already testable). Build:
  replay endpoint with server-side verification (fold moves through the engine,
  compare to stored result, flag mismatches), history page, replay page.
- **Phase 5 — Actions:** resign / draw offer / accept / decline / timeout through
  the same transactional path; actions appear on the replay timeline. The
  `actions` repository and shared-seq logic are already in place.

## Session conventions (for any Claude session resuming here)

- **No-AI-code rule is in force** (repo CLAUDE.md): Claude may only write
  tests and docs; all implementation code is written by the user from
  plain-prose pseudocode; reviews happen after the user writes code.
- Imports are `app.`-prefixed; run everything from `tictactoe/backend/`.
- Test suites: `tests/units` (engine), `tests/integration` (DB + service + API).
  Integration tests use throwaway SQLite DBs in `/tmp` and clean up after.
- Lint with `.venv/bin/ruff check app/ tests/`.
