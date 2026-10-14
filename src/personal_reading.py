"""Keep private reading snapshots and a dated, evidence-only personal voice packet."""

import argparse
import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from refresh import content_hash, validate_books

DEFAULT_ROOT = Path.home() / "skn/shane-neeley/personal-kb/reading"
DATE_BASIS = (
    "Amazon last accessed; proxy for recent reading, not a highlight creation or completion date"
)


def access_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value.strip(), "%A, %B %d, %Y").date()


def packet(export: dict, capture: dict, today: date, baseline: dict | None = None) -> dict:
    validate_books(export["books"])
    books = {b["asin"]: b for b in export["books"]}
    start = today - timedelta(days=6)
    recent = []
    for asin, raw in capture.get("access_dates", {}).items():
        accessed = access_date(raw)
        if start <= accessed <= today and asin in books:
            b = books[asin]
            recent.append(
                {
                    "asin": asin,
                    "title": b["title"],
                    "author": b["author"],
                    "last_accessed": accessed.isoformat(),
                    "highlights": b["highlights"],
                }
            )
    recent.sort(key=lambda b: (b["last_accessed"], b["asin"]), reverse=True)
    added = None
    if baseline is not None:
        prior = {(b["asin"], h["id"]) for b in baseline["books"] for h in b["highlights"]}
        added = sum(
            (b["asin"], h["id"]) not in prior for b in export["books"] for h in b["highlights"]
        )
    return {
        "as_of": today.isoformat(),
        "window_start": start.isoformat(),
        "window_end": today.isoformat(),
        "date_basis": DATE_BASIS,
        "expires_after": (today + timedelta(days=7)).isoformat(),
        "export_hash": content_hash(export),
        "books": recent,
        "newly_observed_highlights": added,
        "limits": "Highlights are other authors' words; neither endorsement nor evidence of Shane's prose. Newly observed is not newly created this week.",
    }


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".reading-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        Path(temporary).replace(path)
        path.chmod(0o600)
    finally:
        Path(temporary).unlink(missing_ok=True)


def archive(
    root: Path, export: dict, capture: dict, today: date, baseline: dict | None = None
) -> dict:
    result = packet(export, capture, today, baseline)
    digest = result["export_hash"]
    snapshot = root / "snapshots" / f"{today}-{digest[:16]}.json"
    if not snapshot.exists():
        atomic_text(snapshot, json.dumps(export, indent=2, ensure_ascii=False) + "\n")
    capture_text = json.dumps(capture, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    capture_hash = hashlib.sha256(capture_text.encode()).hexdigest()
    run = root / "runs" / f"{today}-{capture_hash[:16]}.json"
    if not run.exists():
        atomic_text(run, capture_text)
    evidence = root / "weeks" / f"{today}-{digest[:16]}.json"
    # Do not overwrite a dated packet with a differently evidenced capture.
    evidence = evidence.with_name(f"{today}-{digest[:16]}-{capture_hash[:8]}.json")
    if not evidence.exists():
        atomic_text(evidence, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# Current personal reading context",
        "",
        f"Window: {result['window_start']} through {today} (America/Los_Angeles).",
        f"Use through {result['expires_after']}; then treat as historical until refreshed.",
        f"Date basis: {DATE_BASIS}.",
        "",
        "This is supporting context for personal writing when relevant. Preserve the stable voice in ~/VOICE.md. Do not infer beliefs, experiences, diagnoses or author imitation.",
        "",
        f"Full snapshot: [{snapshot.name}](snapshots/{snapshot.name})",
        f"Evidence and highlight IDs: [{evidence.name}](weeks/{evidence.name})",
        "",
        "## Recent access signals",
        "",
    ]
    for b in result["books"]:
        lines.append(
            f"- {b['last_accessed']}: {b['title']} — {b['author']} ({len(b['highlights'])} highlights, ASIN {b['asin']})."
        )
    if not result["books"]:
        lines.append(
            "No dated notebook access signals in this window. Do not fill the gap with undated or older books."
        )
    lines += [
        "",
        "## Editorial use",
        "",
        "Choose at most one or two relevant moves after inspecting the evidence: a question, rhythm, concrete image, or emphasis. These are tentative drafting choices, not permanent voice rules. Keep attribution when discussing a source. Fresh dates alone do not make a passage relevant.",
    ]
    atomic_text(root / "current.json", json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    atomic_text(root / "current.md", "\n".join(lines) + "\n")
    return {
        "snapshot": str(snapshot),
        "packet": str(evidence),
        "recent_books": len(result["books"]),
        "as_of": str(today),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, default=Path("data/highlights.json"))
    parser.add_argument("--capture", type=Path, default=Path("data/chrome-capture.txt"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=datetime.now(ZoneInfo("America/Los_Angeles")).date(),
    )
    args = parser.parse_args()
    export = json.loads(args.export.read_text())
    capture = json.loads(args.capture.read_text())
    baseline = json.loads(args.baseline.read_text()) if args.baseline else None
    captured = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00"))
    if captured.astimezone(ZoneInfo("America/Los_Angeles")).date() != args.as_of:
        raise ValueError("Use the capture's local date; do not relabel old evidence as current")
    print(json.dumps(archive(args.root, export, capture, args.as_of, baseline)))


if __name__ == "__main__":
    main()
