# AGENTS.md

## Commands

```
uv sync                          # install deps (NOT pip install)
uv run uvicorn autodownloader.main:app --host 0.0.0.0 --port 8000   # dev server
uv run python test_app.py        # run all tests (plain asserts, no framework)
```

- There is **no lint, typecheck, or formatter** configured. Do not try to run `ruff`, `mypy`, `pylint`, or `black`.
- There is **no test runner** — tests are bare Python functions printed from `if __name__ == "__main__"`. No way to run a single test from CLI.

## Architecture

- Single Python package at `src/autodownloader/` (FastAPI + Uvicorn + SQLite/aiosqlite + yt-dlp + FFmpeg + Jinja2).
- All endpoints live in `main.py`. `database.py` handles SQLite CRUD. `processor.py` handles yt-dlp download + FFmpeg processing.
- Frontend is a single `index.html` template with embedded CSS/vanilla JS (no framework).
- `pyproject.toml` declares a script entrypoint: `autodownloader` → `autodownloader.main:main`.

## Gotchas

- **Paths are relative to CWD**, not source file. `DB_PATH = Path("data/jobs.db")` and `Path("downloads")` resolve from wherever the process is launched. Docker entrypoint is `/app`, dev server should be run from repo root.
- **Python >= 3.13 required** (`requires-python = ">=3.13"`). Enforced by uv.
- **Logging is initialized in `lifespan()`**, not at module level. If `main.py` is imported outside the lifespan context (e.g. tests), logging won't be configured.
- **CI only runs on version tags** (`v*`). No test step in CI — only Docker build + push.
- **FFmpeg is an external binary** — not a Python dependency. Must be on `$PATH`.
