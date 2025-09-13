import argparse
import asyncio
import sys
from pathlib import Path
from .scraper import scrape_kindle_highlights


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Kindle highlights from Amazon's notebook page",
        prog="kindle-highlights"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape highlights from Kindle notebook')
    scrape_parser.add_argument(
        '--out', 
        default='data/highlights.json',
        help='Output JSON file path (default: data/highlights.json)'
    )
    scrape_parser.add_argument(
        '--asin',
        help='Scrape only a specific book by ASIN'
    )
    scrape_parser.add_argument(
        '--headful',
        action='store_true',
        help='Run browser in headful mode (useful for debugging or manual 2FA)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'scrape':
        # Check for .env file
        env_path = Path('.env')
        if not env_path.exists():
            print("Error: .env file not found. Please create one based on .env.example")
            print("Required variables: AMAZON_EMAIL, AMAZON_PASSWORD")
            print("Optional: AMAZON_TOTP_SECRET (for 2FA)")
            sys.exit(1)

        print("Starting Kindle highlights scraper...")
        print(f"Output file: {args.out}")
        if args.asin:
            print(f"Scraping specific book: {args.asin}")
        print(f"Browser mode: {'headful' if args.headful else 'headless'}")
        print()

        try:
            books = asyncio.run(scrape_kindle_highlights(
                output_path=args.out,
                asin=args.asin,
                headless=not args.headful
            ))
            
            total_highlights = sum(len(book.highlights) for book in books)
            print()
            print("Scraping completed successfully!")
            print(f"Books scraped: {len(books)}")
            print(f"Total highlights: {total_highlights}")
            print(f"Output saved to: {args.out}")
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()