import json
import stat
from datetime import date

import pytest

from personal_reading import access_date, archive, packet


def export():
    return {
        "run": {"timestamp": "2026-10-14T03:00:00Z"},
        "books": [
            {
                "asin": "B000000001",
                "title": "Recent",
                "author": "Author",
                "cover_url": "",
                "highlights": [{"id": "a", "text": "Example", "color": "yellow"}],
            },
            {
                "asin": "B000000002",
                "title": "Older",
                "author": "Author",
                "cover_url": "",
                "highlights": [{"id": "b", "text": "Older example", "color": "yellow"}],
            },
        ],
    }


def test_recent_reading_uses_access_dates_not_export_time():
    c = {"access_dates": {"B000000001": "Tuesday, October 13, 2026", "B000000002": "2026-09-04"}}
    result = packet(export(), c, date(2026, 10, 13))
    assert [b["asin"] for b in result["books"]] == ["B000000001"]
    assert result["window_start"] == "2026-10-07"
    assert result["expires_after"] == "2026-10-20"
    assert "not newly created" in result["limits"]


def test_missing_dates_and_future_dates_do_not_invent_recent_reading():
    assert packet(export(), {}, date(2026, 10, 13))["books"] == []
    assert (
        packet(export(), {"access_dates": {"B000000001": "2026-10-14"}}, date(2026, 10, 13))[
            "books"
        ]
        == []
    )


def test_newly_observed_is_separate_from_recent_reading():
    result = packet(export(), {}, date(2026, 10, 13), {"books": []})
    assert result["newly_observed_highlights"] == 2
    assert result["books"] == []


def test_snapshots_are_private_idempotent_and_keep_history(tmp_path):
    c = {"access_dates": {"B000000001": "2026-10-13"}}
    first = archive(tmp_path, export(), c, date(2026, 10, 13))
    archive(tmp_path, export(), c, date(2026, 10, 13))
    assert len(list((tmp_path / "snapshots").glob("*.json"))) == 1
    archive(tmp_path, export(), c, date(2026, 10, 20))
    assert len(list((tmp_path / "snapshots").glob("*.json"))) == 2
    assert json.loads((tmp_path / "current.json").read_text())["books"] == []
    for f in tmp_path.rglob("*"):
        assert stat.S_IMODE(f.stat().st_mode) == (0o700 if f.is_dir() else 0o600)
    assert first["recent_books"] == 1


def test_unrecognized_date_is_reported_instead_of_guessed():
    with pytest.raises(ValueError):
        access_date("recently")
