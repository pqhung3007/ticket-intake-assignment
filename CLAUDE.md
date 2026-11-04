# Working rules for AI assistants in this repo

## Git
- Do NOT push. The repository owner (pqhung3007) pushes all code. Commit locally only,
  unless the owner explicitly asks for a push in that moment.
- No co-author lines or AI attribution trailers in commit messages
  (no `Co-Authored-By`, no session links).
- Commit author is the repository owner (repo-local git config).

## Structure (agreed)
- backend/: FastAPI, organised by feature (`app/tickets`, `app/users`) with a shared core
  (`app/core`, `app/db`, `app/auth`). Inside a feature: router -> service -> repository;
  `policy.py` holds pure authorization rules. Routers contain no SQL; repositories contain
  no permission checks; `core/` never imports from features.
- frontend/: React + Vite + shadcn/ui, organised by feature (`src/features/*`). Data access only
  through `features/*/api` (TanStack Query); API types generated from the backend OpenAPI.
- Database: SQLAlchemy 2 (async) + Alembic. Never edit an applied migration; add a new one.

## Checks before committing
- backend: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest`
