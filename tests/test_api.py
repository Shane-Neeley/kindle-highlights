import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app import app, set_scrape_callable


class DummyHighlight:
    def __init__(self, ident: str):
        self.id = ident
        self.color = "yellow"
        self.text = "sample"
        self.page = None
        self.location = 10
        self.note = None


class DummyBook:
    def __init__(self, asin: str, highlight_ids: list[str]):
        self.asin = asin
        self.title = "Test Book"
        self.author = "Author"
        self.cover_url = "http://example.com/cover"
        self.highlights = [DummyHighlight(hid) for hid in highlight_ids]


@pytest.fixture(autouse=True)
def reset_scrape_callable() -> Any:
    original = app.state.scrape_callable
    yield
    set_scrape_callable(app, original)


@pytest.fixture
def cached_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "highlights.json"
    payload = {
        "run": {"timestamp": "2024-01-01T00:00:00Z"},
        "books": [
            {
                "asin": "TEST-ASIN",
                "title": "Cached Book",
                "author": "Author",
                "cover_url": "http://example.com",
                "highlights": [
                    {"id": "h1", "color": "yellow", "text": "cached highlight"},
                    {"id": "h2", "color": "blue", "text": "more text"},
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("HIGHLIGHTS_PATH", str(path))
    return path


@pytest.mark.asyncio
async def test_health_returns_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HIGHLIGHTS_PATH", str(tmp_path / "highlights.json"))

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["output_path"].endswith("highlights.json")


@pytest.mark.asyncio
async def test_books_returns_cached_payload(cached_export: Path) -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/books")

    body = response.json()
    assert response.status_code == 200
    assert body["count"] == 1
    assert body["books"][0]["asin"] == "TEST-ASIN"


@pytest.mark.asyncio
async def test_highlights_flattens_books(cached_export: Path) -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/highlights")

    body = response.json()
    assert response.status_code == 200
    assert body["count"] == 2
    assert {h["id"] for h in body["highlights"]} == {"h1", "h2"}
    assert all(h["asin"] == "TEST-ASIN" for h in body["highlights"])


@pytest.mark.asyncio
async def test_scrape_uses_injected_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HIGHLIGHTS_PATH", str(tmp_path / "export.json"))

    async def fake_scrape(**kwargs: Any):
        return [DummyBook("ASIN-1", ["a", "b"]), DummyBook("ASIN-2", ["c"])]

    set_scrape_callable(app, fake_scrape)

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/scrape", json={"asin": "ASIN-1", "fresh": True})

    body = response.json()
    assert response.status_code == 200
    assert body["asin"] == "ASIN-1"
    assert body["books"] == 2
    assert body["highlights"] == 3
    assert body["resume"] is False
