from copy import deepcopy

import pytest

from refresh import content_hash, merge, plan
from scraper import iso_timestamp


def book(asin="B000000001", text="Example highlight"):
    return {
        "asin": asin,
        "title": "Example",
        "author": "Author",
        "cover_url": "",
        "highlights": [{"id": "example", "text": text, "color": "yellow"}],
    }


def capture(books):
    return {
        "books": books,
        "library": [{"asin": b["asin"]} for b in books],
        "counts": {b["asin"]: len(b["highlights"]) for b in books},
        "captured_at": iso_timestamp(),
    }


def test_content_comparison_ignores_time_order_and_object_key_order():
    a = {"run": {"timestamp": "old"}, "books": [book(), book("B000000002")]}
    b = deepcopy(a)
    b["run"]["timestamp"] = "new"
    b["books"].reverse()
    assert content_hash(a) == content_hash(b)
    b["books"][0]["highlights"][0]["text"] = "Edited, same count"
    assert content_hash(a) != content_hash(b)


def test_plan_refreshes_new_recent_moved_and_oldest_checked():
    library = [{"asin": f"B{i:09}"} for i in range(6)]
    baseline = {"books": [book(b["asin"]) for b in library[:5]]}
    state = {
        "checked": {"B000000002": "2026-10-10"},
        "library_order": ["B000000000", "B000000002", "B000000001"],
    }
    assert plan(library, baseline, state, recent=1, audit=1) == [
        "B000000005",
        "B000000000",
        "B000000001",
    ]


def test_partial_refresh_preserves_other_books_and_noop_timestamp():
    baseline = {"run": {"timestamp": "old"}, "books": [book(), book("B000000002")]}
    assert merge(baseline, capture([book()]), ["B000000001"]) == baseline
    result = merge(baseline, capture([book(text="Updated")]), ["B000000001"])
    assert len(result["books"]) == 2
    assert result["books"][1] == baseline["books"][1]


@pytest.mark.parametrize("failure", ["count", "missing", "duplicate", "stale"])
def test_invalid_or_incomplete_capture_is_rejected(failure):
    baseline = {"books": [book()]}
    data = capture([book()])
    if failure == "count":
        data["counts"]["B000000001"] = 2
    elif failure == "missing":
        data["books"] = []
    elif failure == "duplicate":
        data["books"].append(book())
    else:
        data["captured_at"] = "2020-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        merge(baseline, data, ["B000000001"])
