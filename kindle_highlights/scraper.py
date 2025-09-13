import asyncio
import os
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pyotp
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page
from .parser import Book, parse_book_library, parse_book_from_annotations_page


class KindleScraper:
    def __init__(self, headless: bool = True):
        load_dotenv()
        self.headless = headless
        self.email = os.getenv("AMAZON_EMAIL")
        self.password = os.getenv("AMAZON_PASSWORD")
        self.totp_secret = os.getenv("AMAZON_TOTP_SECRET")

        if not self.email or not self.password:
            raise ValueError(
                "AMAZON_EMAIL and AMAZON_PASSWORD must be set in .env file"
            )

        self.auth_state_path = Path("playwright/.auth/user.json")
        self.auth_state_path.parent.mkdir(parents=True, exist_ok=True)

    async def authenticate(self, page: Page) -> bool:
        """Authenticate with Amazon account."""
        print("Navigating to Amazon Kindle notebook...")
        await page.goto("https://read.amazon.com/kp/notebook?ref_=k4w_ms_notebook")

        # Wait for either login form or already logged in content
        try:
            await page.wait_for_selector(
                'input[name="email"], #kp-notebook-library', timeout=10000
            )
        except Exception as e:
            print(f"Page took too long to load: {e}")
            return False

        # Check if already logged in
        if await page.locator("#kp-notebook-library").count() > 0:
            print("Already logged in!")
            return True

        # Fill in email
        email_input = page.locator('input[name="email"]')
        if await email_input.count() > 0:
            print("Entering email...")
            await email_input.fill(self.email)
            await page.click('input[type="submit"]')
            await page.wait_for_timeout(2000)

        # Fill in password
        password_input = page.locator('input[name="password"]')
        if await password_input.count() > 0:
            print("Entering password...")
            await password_input.fill(self.password)
            await page.click('input[type="submit"]')
            await page.wait_for_timeout(3000)

        # Handle TOTP if required
        totp_input = page.locator('input[name="otpCode"]')
        if await totp_input.count() > 0:
            if self.totp_secret:
                totp = pyotp.TOTP(self.totp_secret)
                code = totp.now()
                print(f"Entering TOTP code: {code}")
                await totp_input.fill(code)
                await page.click('input[type="submit"]')
                await page.wait_for_timeout(3000)
            else:
                print("TOTP required but AMAZON_TOTP_SECRET not set.")
                if not self.headless:
                    print("Please complete 2FA manually in the browser window.")
                    await page.wait_for_selector("#kp-notebook-library", timeout=60000)
                else:
                    return False

        # Wait for successful login
        try:
            await page.wait_for_selector("#kp-notebook-library", timeout=15000)
            print("Successfully authenticated!")
            return True
        except Exception as e:
            print(f"Authentication failed - could not find notebook library: {e}")
            return False

    async def get_book_list(self, page: Page) -> List[dict]:
        """Get list of all annotated books."""
        print("Getting list of annotated books...")

        # Scroll to load all books
        library_container = page.locator("#library-section")
        await library_container.scroll_into_view_if_needed()

        # Scroll to bottom to load all books
        last_count = 0
        stable_count = 0

        while stable_count < 3:  # Stop after count is stable for 3 checks
            await page.evaluate(
                "document.querySelector('#library-section .a-scroller').scrollTo(0, document.querySelector('#library-section .a-scroller').scrollHeight)"
            )
            await page.wait_for_timeout(2000)

            current_count = await page.locator(
                "#kp-notebook-library .kp-notebook-library-each-book"
            ).count()

            if current_count == last_count:
                stable_count += 1
            else:
                stable_count = 0
                last_count = current_count

            print(f"Found {current_count} books...")

        # Get the HTML and parse books
        library_element = page.locator("#kp-notebook-library")
        if await library_element.count() == 0:
            print("Warning: Could not find #kp-notebook-library element")
            print("Saving full page HTML for debugging...")
            page_html = await page.content()
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page_html)
            return []

        library_html = await library_element.inner_html()
        books = parse_book_library(library_html)

        print(f"Total books found: {len(books)}")
        return books

    async def scrape_book_highlights(self, page: Page, asin: str) -> Optional[Book]:
        """Scrape highlights for a specific book."""
        print(f"Scraping highlights for book {asin}...")

        # Click on the book to load its annotations
        book_link = page.locator(f"#kp-notebook-library #{asin} a")
        await book_link.click()
        await page.wait_for_timeout(2000)

        # Wait for annotations to load
        try:
            await page.wait_for_selector("#kp-notebook-annotations", timeout=10000)
        except Exception as e:
            print(f"Failed to load annotations for book {asin}: {e}")
            return None

        # Scroll to load all highlights
        last_count = 0
        stable_count = 0

        while stable_count < 3:
            await page.evaluate(
                "document.querySelector('#annotation-scroller').scrollTo(0, document.querySelector('#annotation-scroller').scrollHeight)"
            )
            await page.wait_for_timeout(2000)

            current_count = await page.locator(
                "#kp-notebook-annotations .kp-notebook-highlight"
            ).count()

            if current_count == last_count:
                stable_count += 1
            else:
                stable_count = 0
                last_count = current_count

        # Check for truncation banner
        truncation_banner = page.locator("#kp-notebook-hidden-annotations-summary")
        if await truncation_banner.count() > 0:
            print(
                f"Warning: Highlights for book {asin} may be truncated due to export limits"
            )

        # Get the full page HTML and parse
        page_html = await page.content()
        book = parse_book_from_annotations_page(page_html)

        if book:
            print(f"Found {len(book.highlights)} highlights for '{book.title}'")

        return book

    async def scrape_all_books(self, specific_asin: Optional[str] = None, output_path: str = "highlights.json", resume: bool = True) -> List[Book]:
        """Scrape highlights from all books or a specific book."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            # Load auth state if it exists
            if self.auth_state_path.exists():
                context = await browser.new_context(
                    storage_state=str(self.auth_state_path)
                )
            else:
                context = await browser.new_context()

            page = await context.new_page()

            try:
                # Authenticate
                if not await self.authenticate(page):
                    raise Exception("Authentication failed")

                # Save auth state for future use
                await context.storage_state(path=str(self.auth_state_path))

                books = []

                if specific_asin:
                    # Scrape specific book
                    book = await self.scrape_book_highlights(page, specific_asin)
                    if book:
                        books.append(book)
                        self.save_book_progressively(book, output_path)
                else:
                    # Load existing data to check for already processed books
                    existing_data = self.load_existing_data(output_path) if resume else {"books": []}
                    existing_asins = self.get_existing_book_asins(existing_data)

                    # Get all books and scrape each one
                    book_list = await self.get_book_list(page)
                    total_books = len(book_list)
                    processed_count = 0

                    for book_info in book_list:
                        asin = book_info["asin"]

                        # Skip if already processed and resume is enabled
                        if resume and asin in existing_asins:
                            print(f"Skipping already processed book {asin}")
                            processed_count += 1
                            continue

                        book = await self.scrape_book_highlights(page, asin)
                        if book:
                            books.append(book)
                            # Save immediately after processing each book
                            self.save_book_progressively(book, output_path)

                        processed_count += 1
                        print(f"Progress: {processed_count}/{total_books} books processed")

                return books

            finally:
                await browser.close()

    def load_existing_data(self, output_path: str) -> dict:
        """Load existing highlights data from JSON file."""
        if not Path(output_path).exists():
            return {"run": {"timestamp": datetime.now().isoformat() + "Z"}, "books": []}

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load existing file {output_path}: {e}")
            return {"run": {"timestamp": datetime.now().isoformat() + "Z"}, "books": []}

    def get_existing_book_asins(self, data: dict) -> set:
        """Get set of ASINs that already exist in the data."""
        return {book["asin"] for book in data.get("books", [])}

    def book_to_dict(self, book: Book) -> dict:
        """Convert a Book object to dictionary format."""
        book_data = {
            "asin": book.asin,
            "title": book.title,
            "author": book.author,
            "cover_url": book.cover_url,
            "highlights": [],
        }

        for highlight in book.highlights:
            highlight_data = {
                "id": highlight.id,
                "color": highlight.color,
                "text": highlight.text,
            }

            if highlight.page is not None:
                highlight_data["page"] = highlight.page
            if highlight.location is not None:
                highlight_data["location"] = highlight.location
            if highlight.note:
                highlight_data["note"] = highlight.note

            book_data["highlights"].append(highlight_data)

        return book_data

    def save_book_progressively(self, book: Book, output_path: str):
        """Save a single book to the JSON file progressively."""
        # Load existing data
        data = self.load_existing_data(output_path)

        # Check if book already exists and update or add
        existing_asins = {b["asin"] for b in data["books"]}
        book_dict = self.book_to_dict(book)

        if book.asin in existing_asins:
            # Update existing book
            for i, existing_book in enumerate(data["books"]):
                if existing_book["asin"] == book.asin:
                    data["books"][i] = book_dict
                    break
            print(f"Updated book '{book.title}' with {len(book.highlights)} highlights")
        else:
            # Add new book
            data["books"].append(book_dict)
            print(f"Added book '{book.title}' with {len(book.highlights)} highlights")

        # Update timestamp
        data["run"]["timestamp"] = datetime.now().isoformat() + "Z"

        # Save to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_to_json(self, books: List[Book], output_path: str):
        """Export scraped books to JSON file (batch mode - kept for compatibility)."""
        data = {"run": {"timestamp": datetime.now().isoformat() + "Z"}, "books": []}

        for book in books:
            book_data = self.book_to_dict(book)
            data["books"].append(book_data)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(books)} books to {output_path}")


async def scrape_kindle_highlights(
    output_path: str, asin: Optional[str] = None, headless: bool = True, resume: bool = True
):
    """Main function to scrape Kindle highlights."""
    scraper = KindleScraper(headless=headless)
    books = await scraper.scrape_all_books(specific_asin=asin, output_path=output_path, resume=resume)

    # Only export at the end if we got any new books and we're not using progressive saving
    if not resume and books:
        scraper.export_to_json(books, output_path)

    return books
