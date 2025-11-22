# IMP-001: Type Checking & Linting Modernization

## Overview

Amazon’s Kindle Notebook DOM changes frequently, so regressions creep in when parser edge cases or async Playwright calls drift from expectations. This IMP introduces a lightweight quality gate built around Ruff (lint+format), MyPy (type checking), and `pre-commit` automation so contributors catch issues before shipping new scraping logic.

## Motivation

- **Parser fragility**: changes in BeautifulSoup selectors produce runtime errors that unit tests may not catch immediately.
- **Async scraping risks**: improper `await` usage or forgotten imports can sneak past `pytest` until runtime.
- **Contributor experience**: the repo currently relies on manual discipline; there is no advertised lint/type workflow.

## Research & References

- Ruff (lint + formatter): https://docs.astral.sh/ruff/
- Ty (fast typed-Python checker by Astral): https://docs.astral.sh/ty/
- pre-commit framework: https://pre-commit.com/
- uv build command (packaging smoke test): https://docs.astral.sh/uv/guides/build/

## Proposal

1. **Add Ruff configuration**
   - Define a `[tool.ruff]` section in `pyproject.toml` covering `lint.select = ["E", "F", "I", "UP", "ASYNC"]` and enable the Ruff formatter to replace `black`.
   - Expose commands: `uv run ruff check src tests` and `uv run ruff format`.
2. **Introduce Ty for lightweight type checking**
   - Document installing Ty via `uv tool install ty` and run it against `src` + `tests` (`ty check src tests`).
   - Keep the existing annotations in `parser.py`/`scraper.py` so Ty can flag obvious typing mistakes without the heaviness of full MyPy strict mode.
3. **Adopt src/ layout for package structure**
   - Code now lives directly under `src/` (modules: `parser.py`, `scraper.py`, `main.py`, `app.py`) to keep imports simple and avoid accidental relative imports.
   - Update `pyproject.toml` to point tooling at `src/` and keep editable installs clean.
   - Benefits: Prevents accidental imports of uninstalled package, clearer separation of source vs. build artifacts, better editable install behavior.
   - Update all tool configurations to reference `src/` modules.
4. **Pre-commit hooks**
   - Create `.pre-commit-config.yaml` with hooks:
     - `ruff` (lint)
     - `ruff-format`
     - `ty` via `repo: local`, command `ty check src tests`
     - Optional `pytest` hook guarded behind `stages: [manual]` for contributors who want to run it locally.
   - Document installation: `uv tool install pre-commit` and `pre-commit install`.
5. **CI-friendly packaging smoke test**
   - Add a `make build`-style alias (or `uv run python -m build`) to ensure the package metadata is valid.
   - Mention this command in README's contributor section and consider adding it to future CI once GitHub workflows are configured.

- Package structure follows src/ layout with code in `src/` (flat modules).
- `pyproject.toml` configured for src layout with proper package discovery.
- Ruff config lives in `pyproject.toml`, and running `uv run ruff check`, `uv run ruff format`, and `ty check src tests` returns zero errors on main.
- `.pre-commit-config.yaml` exists, documented in README, and `pre-commit run --all-files` runs the Ruff + Ty hooks through `uv`.
- README gains a "Quality Checks" subsection listing the new commands plus instructions for enabling pre-commit.
- Optional: a short CI note describing how to integrate these commands when GitHub Actions or another runner becomes available.

Once merged, subsequent IMPs can build on this foundation (e.g., adding `pytest` coverage gates or uploading build artifacts).

## Status: ✅ COMPLETED

All objectives achieved as of 2025-11-22:

- ✅ **Ruff**: Configured in `pyproject.toml` with lint rules (E, W, F, I, B, UP, ASYNC) and formatter. Commands: `uv run ruff check src tests` and `uv run ruff format`.
- ✅ **Ty**: Type checking via `ty check src tests` passes cleanly. Install: `uv tool install ty`.
- ✅ **Pre-commit**: Hooks configured in `.pre-commit-config.yaml` for ruff, ruff-format, and ty. Install: `uv tool install pre-commit && pre-commit install`.
- ✅ **src/ layout**: Code lives under `src/` with flat modules to prevent accidental imports and keep editable installs clean.
- ✅ **Type annotations**: Parser and scraper modules use `TypedDict`, `Tag` checks, and proper return types.
- ✅ **Build**: `uv build` creates wheel and sdist successfully.
- ✅ **Tests**: All 7 tests passing with pytest.
- ✅ **Documentation**: README, CLAUDE.md, and AGENTS.md updated to reflect src layout and quality check workflows.

## Validation

Run these commands to verify:

```bash
uv sync
uv run pytest -v
uv run ruff check src tests
uv run ruff format --check src tests
ty check src tests
uv build
pre-commit run --all-files
```
