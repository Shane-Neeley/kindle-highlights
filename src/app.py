"""FastAPI service for Kindle highlights scraping and cache access."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scraper import ExportData, scrape_kindle_highlights

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


ScrapeCallable = Callable[..., Awaitable[list[Any]]]
DEFAULT_OUTPUT = "data/highlights.json"


class ScrapeRequest(BaseModel):
    asin: str | None = Field(default=None, description="Scrape a single ASIN when provided")
    headful: bool = Field(default=False, description="Run the browser in headful mode")
    fresh: bool = Field(default=False, description="Ignore cached progress and rescrape all books")


class ScrapeResponse(BaseModel):
    asin: str | None
    books: int
    highlights: int
    output_path: str
    resume: bool
    timestamp: str


def iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def get_output_path() -> Path:
    return Path(os.getenv("HIGHLIGHTS_PATH", DEFAULT_OUTPUT))


def get_scrape_callable(app: FastAPI) -> ScrapeCallable:
    return getattr(app.state, "scrape_callable", scrape_kindle_highlights)


def set_scrape_callable(app: FastAPI, func: ScrapeCallable) -> None:
    app.state.scrape_callable = func


def load_cached_export() -> ExportData:
    output_path = get_output_path()

    if not output_path.exists():
        return {"run": {"timestamp": None}, "books": []}

    try:
        payload = output_path.read_text(encoding="utf-8")
        data = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Failed to read cached highlights", exc_info=exc)
        raise HTTPException(
            status_code=500, detail="Cached highlights could not be loaded"
        ) from exc

    if not isinstance(data, dict) or "books" not in data or "run" not in data:
        raise HTTPException(status_code=500, detail="Cached highlights are missing expected keys")

    return cast(ExportData, data)


app = FastAPI(title="Kindle Highlights", version="0.1.0")
app.state.scrape_lock = asyncio.Lock()
app.state.scrape_callable = scrape_kindle_highlights


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": iso_timestamp(),
        "output_path": str(get_output_path()),
    }


@app.get("/books")
async def list_books() -> dict[str, Any]:
    cached = load_cached_export()
    return {
        "run": cached.get("run", {}),
        "count": len(cached.get("books", [])),
        "books": cached.get("books", []),
    }


@app.get("/highlights")
async def list_highlights() -> dict[str, Any]:
    cached = load_cached_export()
    highlights: list[dict[str, Any]] = []

    for book in cached.get("books", []):
        for highlight in book.get("highlights", []):
            enriched = {
                **highlight,
                "asin": book.get("asin"),
                "title": book.get("title"),
                "author": book.get("author"),
            }
            highlights.append(enriched)

    return {
        "run": cached.get("run", {}),
        "count": len(highlights),
        "highlights": highlights,
    }


@app.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(payload: ScrapeRequest) -> ScrapeResponse:
    output_path = get_output_path()
    resume = not payload.fresh
    headless = not payload.headful

    lock: asyncio.Lock = app.state.scrape_lock
    if lock.locked():
        raise HTTPException(status_code=409, detail="A scrape is already running")

    scrape_func = get_scrape_callable(app)

    async with lock:
        try:
            books = await scrape_func(
                output_path=str(output_path),
                asin=payload.asin,
                headless=headless,
                resume=resume,
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Scrape failed", exc_info=exc)
            raise HTTPException(status_code=500, detail="Scrape failed") from exc

    total_highlights = sum(len(book.highlights) for book in books)

    return ScrapeResponse(
        asin=payload.asin,
        books=len(books),
        highlights=total_highlights,
        output_path=str(output_path),
        resume=resume,
        timestamp=iso_timestamp(),
    )


__all__ = ["app", "get_output_path", "set_scrape_callable"]
