# IMP-002: Service API & Containerization

## Overview

Expose the Kindle highlights workflow as a lightweight FastAPI service with a Docker build so downstream tools can trigger scrapes, read cached exports, and monitor health without shell access. The service will live in `src/app.py`, ship with a simple `Dockerfile`, and run via Uvicorn for production-friendly defaults.

## Motivation

- **Integration surface**: HTTP endpoints let note-taking apps, CRON jobs, or webhooks request new scrapes and fetch highlights without depending on the CLI or Python environment.
- **Operational clarity**: A `/health` probe and structured logging make it easier to run this in containers or PaaS (Fly.io, Render, ECS) while keeping credentials in env vars.
- **Reusability**: Containerizing the service with a reproducible image ensures contributors and consumers run the same stack (Playwright + dependencies) without bespoke setup.

## Research & References

- FastAPI: https://fastapi.tiangolo.com/
- Uvicorn deployment notes: https://www.uvicorn.org/deployment/
- Docker multi-stage Python builds: https://docs.docker.com/develop/develop-images/multistage-build/

## Proposal

1. **HTTP service entrypoint**
   - Create `src/app.py` with a minimal `FastAPI` app exposing:
     - `GET /health` returning version + timestamp.
     - `POST /scrape` accepting optional `asin`, delegating to existing scrape logic (reuse `scraper.py`), and persisting to `data/highlights.json`.
     - `GET /books` and `GET /highlights` reading the current JSON export for consumers that only need cached data.
   - Add basic logging + timeout handling; keep auth secrets in env (`AMAZON_EMAIL`, `AMAZON_PASSWORD`).
2. **Container packaging**
   - Add a `Dockerfile` using Python 3.13-slim with multi-stage `uv` install to keep images small.
   - Copy `pyproject.toml`/`uv.lock`, run `uv sync --no-dev --frozen`, then copy `src/`, `data/`, and `playwright/` auth state if present.
   - Default CMD: `uv run uvicorn src.app:app --host 0.0.0.0 --port 8000 --proxy-headers`.
3. **Local ergonomics**
   - Document `uv run uvicorn src.app:app --reload` for local dev and `docker build -t kindle-highlights . && docker run -p 8000:8000 ...` for container runs.
   - Provide `.env.example` notes for service-specific envs (rate limits, headful toggle) and mention how to mount `data/` for persistence.
4. **Validation & tests**
   - Add lightweight FastAPI route tests with `httpx.AsyncClient` mocking scraper calls to avoid live Amazon traffic.
   - Smoke test the Docker image via `docker run --rm kindle-highlights curl localhost:8000/health`.

## Acceptance Criteria

- `src/app.py` defines a FastAPI app with `/health`, `/scrape`, `/books`, and `/highlights` routes, wired into existing scraping/parsing functions.
- A production-ready `Dockerfile` builds a runnable image via `docker build` and defaults to `uvicorn` serving the app.
- README gains a short "Service" section covering local run, Docker usage, and required environment variables.
- Tests cover route success paths without hitting real Amazon endpoints; CI (or local `uv run pytest`) passes.
- Container and local server avoid committing credentials or Playwright auth state; documented paths for mounting data.

## Current Progress

- Proposed: outlines service shape, container approach, and acceptance criteria.
