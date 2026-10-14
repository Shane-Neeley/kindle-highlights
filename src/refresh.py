"""Offline planning and validated merge for the signed-in Chrome workflow."""

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scraper import KindleScraper, iso_timestamp, validate_asin


def content_hash(data: dict) -> str:
    books = deepcopy(data["books"])
    for book in books:
        book["highlights"].sort(key=lambda h: h["id"])
    books.sort(key=lambda b: b["asin"])
    return hashlib.sha256(
        json.dumps(books, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate_books(books: list[dict]) -> None:
    seen = set()
    for book in books:
        asin = validate_asin(book["asin"])
        if asin != book["asin"] or asin in seen or not book["title"]:
            raise ValueError("Invalid or duplicate book")
        seen.add(asin)
        ids = set()
        for highlight in book["highlights"]:
            if not highlight.get("id") or not highlight.get("text") or highlight["id"] in ids:
                raise ValueError(f"Invalid or duplicate highlight in {asin}")
            ids.add(highlight["id"])


def plan(
    library: list[dict], baseline: dict, state: dict, recent: int = 20, audit: int = 20
) -> list[str]:
    """New books + recent books + least recently checked older books."""
    known = {b["asin"] for b in baseline["books"]}
    selected = [b["asin"] for b in library if b["asin"] not in known]
    selected.extend(b["asin"] for b in library[:recent])
    previous_order = {asin: i for i, asin in enumerate(state.get("library_order", []))}
    selected.extend(
        b["asin"]
        for i, b in enumerate(library)
        if b["asin"] in previous_order and i < previous_order[b["asin"]]
    )
    older = [b["asin"] for b in library[recent:]]
    older.sort(key=lambda asin: (state.get("checked", {}).get(asin, ""), asin))
    selected.extend(older[:audit])
    return list(dict.fromkeys(selected))


def merge(baseline: dict, capture: dict, required: list[str]) -> dict:
    validate_books(baseline["books"])
    validate_books(capture["books"])
    library = {b["asin"] for b in capture["library"]}
    if not library or len(library) != len(capture["library"]):
        raise ValueError("Empty or duplicate library inventory")
    refreshed = {b["asin"]: b for b in capture["books"]}
    captured_at = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00"))
    age = datetime.now(UTC) - captured_at
    if age < timedelta(minutes=-5) or age > timedelta(hours=24):
        raise ValueError("Capture is stale; read the notebook again")
    if not set(required).issubset(refreshed) or not set(refreshed).issubset(library):
        raise ValueError("Capture does not cover the refresh plan")
    counts = capture.get("counts", {})
    for asin, book in refreshed.items():
        if counts.get(asin) != len(book["highlights"]):
            raise ValueError(f"Missing count verification or truncated export: {asin}")
    # Never infer deletion from a partial library response. Preserve absent books.
    books = {b["asin"]: b for b in baseline["books"]}
    books.update(refreshed)
    result = {"run": {"timestamp": iso_timestamp()}, "books": list(books.values())}
    if content_hash(result) == content_hash(baseline):
        return baseline
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "merge", "compare"])
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--state", type=Path, default=Path("data/refresh-state.json"))
    parser.add_argument("--out", type=Path, default=Path("data/highlights.json"))
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    state = json.loads(args.state.read_text()) if args.state.exists() else {}
    capture = json.loads(args.capture.read_text()) if args.capture else {}
    if args.command == "compare":
        validate_books(baseline["books"])
        candidate = json.loads(args.out.read_text())
        validate_books(candidate["books"])
        print(json.dumps({"changed": content_hash(baseline) != content_hash(candidate)}))
        return
    required = plan(capture["library"], baseline, state)
    if args.command == "plan":
        print(json.dumps({"asins": required, "library_books": len(capture["library"])}))
        return
    result = merge(baseline, capture, required)
    writer = KindleScraper()
    # Immutable, content-addressed baseline backup before updating anything.
    backup = args.out.parent / "backups" / f"{content_hash(baseline)}.json"
    if not backup.exists():
        writer._atomic_write_json(baseline, str(backup))
    writer._atomic_write_json(result, str(args.out))
    checked = state.setdefault("checked", {})
    now = iso_timestamp()
    for book in capture["books"]:
        checked[book["asin"]] = now
    state["last_success"] = now
    state["library_order"] = [b["asin"] for b in capture["library"]]
    writer._atomic_write_json(state, str(args.state))
    print(
        json.dumps(
            {
                "changed": content_hash(result) != content_hash(baseline),
                "books": len(result["books"]),
                "highlights": sum(len(b["highlights"]) for b in result["books"]),
                "refreshed": len(capture["books"]),
            }
        )
    )


if __name__ == "__main__":
    main()
