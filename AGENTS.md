# Repository Guidelines

## Project Structure & Module Organization
The `kindle_highlights/` package contains production code: `scraper.py` drives Playwright login, `parser.py` converts notebook HTML into `Book`/`Highlight` dataclasses, and `__main__.py` exposes the CLI (`python -m kindle_highlights`). Tests and fixtures live under `tests/` (see `tests/fixtures/sample_notebook.html`), while `data/` holds exported highlights and `playwright/` stores persisted browser sessions. Keep credentials in `.env`; never edit `.env.example` without reflecting any new keys.

## Build, Test, and Development Commands
- `uv sync` — install runtime + dev dependencies for Python 3.12.
- `uv run playwright install --with-deps chromium` — install the browser bundle.
- `uv run python -m kindle_highlights scrape --out data/highlights.json` — scrape the full library; add `--asin <ASIN>` for one book.
- `uv run python -m kindle_highlights scrape --headful --asin <ASIN>` — debug selectors or manual 2FA in a visible browser.
- `uv run python -m kindle_highlights scrape --fresh` — ignore previous JSON progress and rescrape every book.
- `uv run pytest -v` — run the parser regression suite; add `-k name` for focused work.

## Coding Style & Naming Conventions
Write modern, type-hinted Python with four-space indentation. Keep modules, functions, and locals in `lower_snake_case`, reserve PascalCase for dataclasses, and use ALL_CAPS only for environment keys. Prefer `pathlib.Path` for file IO, add docstrings only when behavior is non-obvious, and extend JSON output by updating the dataclasses, parser, and serializer together instead of returning loose dicts.

## Testing Guidelines
Pytest is configured via `pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`). Table-driven tests in `tests/test_parser.py` rely on the sanitized fixture under `tests/fixtures/`. Add new cases as `test_<behavior>` functions, cover both empty-markup fallbacks and happy paths, and ensure DOM tweaks are validated by running `uv run pytest -v` plus at least one dry scrape before opening a PR.

## Commit & Pull Request Guidelines
Follow the existing history of short, imperative subjects (“Fix book library parsing for updated Amazon HTML structure”), keep them under ~72 characters, and describe the Amazon-side change plus validation commands in the PR body. Include scrape snippets or console logs that prove selectors still work, mention any manual cleanup (e.g., deleting `playwright/.auth/user.json`), and link issues/ASIN regressions when relevant.

## Security & Configuration Tips
Never commit `.env`, Playwright auth state, or real highlight exports. Scrub `data/highlights.json` before sharing logs, prefer dummy ASINs in fixtures, document new environment variables inside `.env.example`, and delete `playwright/` when credentials change to rotate cached login state.
