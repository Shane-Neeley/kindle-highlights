import json
import stat
from pathlib import Path

import pytest

import scraper as scraper_module
from scraper import (
    ExportData,
    KindleScraper,
    is_amazon_error_page,
    iso_timestamp,
    scrape_kindle_highlights,
    validate_asin,
)


def test_validate_asin_normalizes_safe_values() -> None:
    assert validate_asin(" b00x57b4jg ") == "B00X57B4JG"


def test_amazon_generic_error_page_detection_is_specific() -> None:
    assert is_amazon_error_page("Something went wrong")
    assert is_amazon_error_page("  SOMETHING WENT WRONG ")
    assert not is_amazon_error_page("Amazon Sign-In")


@pytest.mark.parametrize(
    "value",
    ["", "short", "B00X57B4JG a", "B00X57B4J!", "#library a"],
)
def test_validate_asin_rejects_unsafe_selector_input(value: str) -> None:
    with pytest.raises(ValueError, match="10 letters or digits"):
        validate_asin(value)


def test_scraper_does_not_require_credentials_for_saved_or_manual_sessions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("AMAZON_EMAIL", raising=False)
    monkeypatch.delenv("AMAZON_PASSWORD", raising=False)

    scraper = KindleScraper(auth_state_path=tmp_path / "session.json")

    assert scraper.has_credentials is False
    assert scraper.headless is False


def test_credentials_mode_requires_both_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("AMAZON_EMAIL", raising=False)
    monkeypatch.delenv("AMAZON_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="requires AMAZON_EMAIL"):
        KindleScraper(
            auth_mode="credentials",
            auth_state_path=tmp_path / "session.json",
        )


def test_interactive_mode_rejects_headless_browser(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="visible browser"):
        KindleScraper(
            headless=True,
            auth_mode="interactive",
            auth_state_path=tmp_path / "session.json",
        )


@pytest.mark.asyncio
async def test_book_load_failure_stops_the_export(tmp_path: Path) -> None:
    class FakeLink:
        async def click(self) -> None:
            pass

    class FakePage:
        def locator(self, _: str) -> FakeLink:
            return FakeLink()

        async def wait_for_selector(self, _: str, **__: object) -> None:
            raise TimeoutError("annotations did not load")

    scraper = KindleScraper(auth_state_path=tmp_path / "session.json")

    with pytest.raises(RuntimeError, match="Failed to load annotations"):
        await scraper.scrape_book_highlights(FakePage(), "B00X57B4JG")  # type: ignore[arg-type]


def test_atomic_export_is_private_and_valid_json(tmp_path: Path) -> None:
    output = tmp_path / "highlights.json"
    scraper = KindleScraper(auth_state_path=tmp_path / "session.json")
    data: ExportData = {
        "run": {"timestamp": "2026-07-25T00:00:00Z"},
        "books": [],
    }

    scraper._atomic_write_json(data, str(output))

    assert json.loads(output.read_text(encoding="utf-8")) == data
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".highlights.json.*.tmp"))


def test_export_timestamp_is_utc() -> None:
    timestamp = iso_timestamp()

    assert timestamp.endswith("Z")
    assert "+" not in timestamp


def test_malformed_existing_export_falls_back_to_empty_data(tmp_path: Path) -> None:
    output = tmp_path / "highlights.json"
    output.write_text('{"books": "not-a-list"}', encoding="utf-8")
    scraper = KindleScraper(auth_state_path=tmp_path / "session.json")

    data = scraper.load_existing_data(str(output))

    assert data["books"] == []


def test_existing_asins_ignore_malformed_entries(tmp_path: Path) -> None:
    scraper = KindleScraper(auth_state_path=tmp_path / "session.json")
    data = {
        "run": {"timestamp": None},
        "books": [
            {"asin": "b00x57b4jg"},
            {"asin": "invalid"},
            {},
            "not-a-book",
        ],
    }

    assert scraper.get_existing_book_asins(data) == {"B00X57B4JG"}  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_single_book_refresh_never_replaces_full_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exported_batches: list[list[object]] = []

    class FakeScraper:
        def __init__(self, **_: object) -> None:
            pass

        async def scrape_all_books(self, **_: object) -> list[object]:
            return [object()]

        def export_to_json(self, books: list[object], output_path: str) -> None:
            exported_batches.append(books)

    monkeypatch.setattr(scraper_module, "KindleScraper", FakeScraper)

    await scrape_kindle_highlights(
        output_path="unused.json",
        asin="B00X57B4JG",
        resume=False,
    )

    assert exported_batches == []


@pytest.mark.asyncio
async def test_full_refresh_replaces_export_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exported_batches: list[tuple[list[object], str]] = []
    scraped_books = [object(), object()]

    class FakeScraper:
        def __init__(self, **_: object) -> None:
            pass

        async def scrape_all_books(self, **_: object) -> list[object]:
            return scraped_books

        def export_to_json(self, books: list[object], output_path: str) -> None:
            exported_batches.append((books, output_path))

    monkeypatch.setattr(scraper_module, "KindleScraper", FakeScraper)

    await scrape_kindle_highlights(output_path="full.json", resume=False)

    assert exported_batches == [(scraped_books, "full.json")]
