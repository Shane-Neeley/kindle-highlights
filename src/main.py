import argparse
import asyncio
import json
from pathlib import Path

from scraper import AUTH_MODES, scrape_kindle_highlights, validate_asin


def argparse_asin(value: str) -> str:
    try:
        return validate_asin(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def export_counts(output_path: str) -> tuple[int, int]:
    """Return total export counts without conflating them with this run."""
    path = Path(output_path)
    if not path.exists():
        return 0, 0
    data = json.loads(path.read_text(encoding="utf-8"))
    books = data.get("books", [])
    return len(books), sum(len(book.get("highlights", [])) for book in books)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Kindle highlights from Amazon's notebook page", prog="kindle-highlights"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    scrape_parser = subparsers.add_parser("scrape", help="Scrape highlights from Kindle notebook")
    scrape_parser.add_argument(
        "--out",
        default="data/highlights.json",
        help="Output JSON file path (default: data/highlights.json)",
    )
    scrape_parser.add_argument("--asin", type=argparse_asin, help="Refresh one 10-character ASIN")
    browser_group = scrape_parser.add_mutually_exclusive_group()
    browser_group.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible browser (requires a saved session or credentials)",
    )
    browser_group.add_argument(
        "--headful",
        dest="headless",
        action="store_false",
        help="Run with a visible browser (default; supports interactive sign-in)",
    )
    refresh_group = scrape_parser.add_mutually_exclusive_group()
    refresh_group.add_argument(
        "--resume",
        action="store_true",
        help="Skip ASINs already in the output (fast recovery, but does not refresh changed books)",
    )
    refresh_group.add_argument(
        "--fresh",
        dest="resume",
        action="store_false",
        help="Refresh every current book (default)",
    )
    scrape_parser.add_argument(
        "--auth",
        choices=sorted(AUTH_MODES),
        default="auto",
        help="Authentication fallback after trying saved session state (default: auto)",
    )
    scrape_parser.set_defaults(headless=False, resume=False)

    args = parser.parse_args()

    if args.command == "scrape":
        print("Starting Kindle highlights scraper...")
        print(f"Output file: {args.out}")
        if args.asin:
            print(f"Scraping specific book: {args.asin}")
        print(f"Browser mode: {'headless' if args.headless else 'visible'}")
        print(f"Authentication: {args.auth} (saved session is always tried first)")
        print(f"Refresh existing books: {'no (--resume)' if args.resume else 'yes'}")
        print()

        try:
            books = asyncio.run(
                scrape_kindle_highlights(
                    output_path=args.out,
                    asin=args.asin,
                    headless=args.headless,
                    resume=args.resume,
                    auth_mode=args.auth,
                )
            )

            total_books, total_highlights = export_counts(args.out)
            print()
            print("Scraping completed successfully!")
            print(f"Books processed this run: {len(books)}")
            print(f"Export totals: {total_books} books, {total_highlights} highlights")
            print(f"Output saved to: {args.out}")

        except Exception as e:  # pragma: no cover - CLI feedback path
            print(f"Error: {e}")
            raise SystemExit(1) from e

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
