from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import pyotp
from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

from parser import Book, parse_book_from_annotations_page, parse_book_library


class HighlightDict(TypedDict):
    id: str
    color: str
    text: str
    page: NotRequired[int]
    location: NotRequired[int]
    note: NotRequired[str]


class BookDict(TypedDict):
    asin: str
    title: str
    author: str
    cover_url: str
    highlights: list[HighlightDict]


class ExportData(TypedDict):
    run: dict[str, str | None]
    books: list[BookDict]


class KindleScraper:
    def __init__(self, headless: bool = True):
        load_dotenv()
        self.headless = headless
        email = os.getenv("AMAZON_EMAIL")
        password = os.getenv("AMAZON_PASSWORD")
        self.totp_secret: str | None = os.getenv("AMAZON_TOTP_SECRET")

        if not email or not password:
            raise ValueError("AMAZON_EMAIL and AMAZON_PASSWORD must be set in .env file")

        self.email: str = email
        self.password: str = password
        self.auth_state_path = Path("playwright/.auth/user.json")
        self.auth_state_path.parent.mkdir(parents=True, exist_ok=True)

    async def authenticate(self, page: Page) -> bool:
        """Authenticate with Amazon account."""
        print("Navigating to Amazon Kindle notebook...")
        await page.goto("https://read.amazon.com/kp/notebook?ref_=k4w_ms_notebook")

        # Wait for either login form or already logged in content
        login_or_library = (
            'input[name="email"]:not([type="hidden"]), '
            'input#ap_email:not([type="hidden"]), '
            "#kp-notebook-library"
        )

        try:
            await page.wait_for_selector(login_or_library, timeout=20000)
        except Exception as e:  # pragma: no cover - network timing
            print(f"Page took too long to load: {e}")
            return False

        # Check if already logged in
        if await page.locator("#kp-notebook-library").count() > 0:
            print("Already logged in!")
            return True

        # Fill in email (or reuse claimed email if Amazon pre-selects account)
        email_input = page.locator(
            'input[name="email"]:not([type="hidden"]), input#ap_email:not([type="hidden"])'
        )
        if await email_input.count() > 0:
            print("Entering email...")
            await email_input.first.fill(self.email)
            await page.click('input[type="submit"], input#continue')
            await page.wait_for_timeout(2000)
        else:
            claimed = page.locator("input#ap-claim")
            if await claimed.count() > 0:
                print("Amazon pre-selected email, continuing to password...")
                continue_btn = page.locator('input#continue, input[type="submit"]#continue')
                if await continue_btn.count() > 0:
                    await continue_btn.first.click()
                    await page.wait_for_timeout(2000)

        # Fill in password
        password_input = page.locator(
            'input[name="password"]:not([type="hidden"]), input#ap_password:not([type="hidden"])'
        )
        if await password_input.count() > 0:
            print("Entering password...")
            await password_input.first.fill(self.password)
            await page.click('input[type="submit"], input#signInSubmit')
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
        except Exception as e:  # pragma: no cover - network timing
            print(f"Authentication failed - could not find notebook library: {e}")
            return False

    async def get_book_list(self, page: Page) -> list[dict[str, str]]:
        """Get list of all annotated books."""
        print("Getting list of annotated books...")

        library_container = page.locator("#library-section")
        await library_container.scroll_into_view_if_needed()

        last_count = 0
        stable_count = 0

        while stable_count < 3:
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

        library_element = page.locator("#kp-notebook-library")
        if await library_element.count() == 0:
            print("Warning: Could not find #kp-notebook-library element")
            print("Saving full page HTML for debugging...")
            page_html = await page.content()
            await asyncio.to_thread(
                Path("debug_page.html").write_text,
                page_html,
                encoding="utf-8",
            )
            return []

        library_html = await library_element.inner_html()
        books = parse_book_library(library_html)

        print(f"Total books found: {len(books)}")
        return books

    async def scrape_book_highlights(self, page: Page, asin: str) -> Book | None:
        """Scrape highlights for a specific book."""
        print(f"Scraping highlights for book {asin}...")

        book_link = page.locator(f"#kp-notebook-library #{asin} a")
        await book_link.click()
        await page.wait_for_timeout(2000)

        try:
            await page.wait_for_selector("#kp-notebook-annotations", timeout=10000)
        except Exception as e:  # pragma: no cover - network timing
            print(f"Failed to load annotations for book {asin}: {e}")
            return None

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

        truncation_banner = page.locator("#kp-notebook-hidden-annotations-summary")
        if await truncation_banner.count() > 0:
            print(f"Warning: Highlights for book {asin} may be truncated due to export limits")

        page_html = await page.content()
        book = parse_book_from_annotations_page(page_html)

        if book:
            print(f"Found {len(book.highlights)} highlights for '{book.title}'")

        return book

    async def scrape_all_books(
        self,
        specific_asin: str | None = None,
        output_path: str = "highlights.json",
        resume: bool = True,
    ) -> list[Book]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            if self.auth_state_path.exists():
                context = await browser.new_context(storage_state=str(self.auth_state_path))
            else:
                context = await browser.new_context()

            page = await context.new_page()

            try:
                if not await self.authenticate(page):
                    raise Exception("Authentication failed")

                await context.storage_state(path=str(self.auth_state_path))

                books: list[Book] = []

                if specific_asin:
                    book = await self.scrape_book_highlights(page, specific_asin)
                    if book:
                        books.append(book)
                        self.save_book_progressively(book, output_path)
                else:
                    existing_data = (
                        self.load_existing_data(output_path)
                        if resume
                        else self._empty_export_data()
                    )
                    existing_asins = self.get_existing_book_asins(existing_data)

                    book_list = await self.get_book_list(page)
                    total_books = len(book_list)
                    processed_count = 0

                    for book_info in book_list:
                        asin = book_info["asin"]

                        if resume and asin in existing_asins:
                            print(f"Skipping already processed book {asin}")
                            processed_count += 1
                            continue

                        book = await self.scrape_book_highlights(page, asin)
                        if book:
                            books.append(book)
                            self.save_book_progressively(book, output_path)

                            processed_count += 1
                            print(f"Progress: {processed_count}/{total_books} books processed")

                return books

            finally:
                await browser.close()

    def _empty_export_data(self) -> ExportData:
        return {"run": {"timestamp": datetime.now().isoformat() + "Z"}, "books": []}

    def load_existing_data(self, output_path: str) -> ExportData:
        """Load existing highlights data from JSON file."""
        if not Path(output_path).exists():
            return self._empty_export_data()

        try:
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load existing file {output_path}: {e}")
            return self._empty_export_data()

        return cast(ExportData, data)

    def get_existing_book_asins(self, data: ExportData) -> set[str]:
        """Get set of ASINs that already exist in the data."""
        return {book["asin"] for book in data["books"]}

    def book_to_dict(self, book: Book) -> BookDict:
        """Convert a Book object to dictionary format."""
        highlights: list[HighlightDict] = []
        book_data: BookDict = {
            "asin": book.asin,
            "title": book.title,
            "author": book.author,
            "cover_url": book.cover_url,
            "highlights": highlights,
        }

        for highlight in book.highlights:
            highlight_data: HighlightDict = {
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

            highlights.append(highlight_data)

        return book_data

    def save_book_progressively(self, book: Book, output_path: str) -> None:
        """Save a single book to the JSON file progressively."""
        data = self.load_existing_data(output_path)

        existing_asins = {b["asin"] for b in data["books"]}
        book_dict = self.book_to_dict(book)

        if book.asin in existing_asins:
            for i, existing_book in enumerate(data["books"]):
                if existing_book["asin"] == book.asin:
                    data["books"][i] = book_dict
                    break
            print(f"Updated book '{book.title}' with {len(book.highlights)} highlights")
        else:
            data["books"].append(book_dict)
            print(f"Added book '{book.title}' with {len(book.highlights)} highlights")

        data["run"]["timestamp"] = datetime.now().isoformat() + "Z"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_to_json(self, books: list[Book], output_path: str) -> None:
        """Export scraped books to JSON file (batch mode - kept for compatibility)."""
        data: ExportData = self._empty_export_data()
        data["books"] = []

        for book in books:
            book_data = self.book_to_dict(book)
            data["books"].append(book_data)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(books)} books to {output_path}")


async def scrape_kindle_highlights(
    output_path: str,
    asin: str | None = None,
    headless: bool = True,
    resume: bool = True,
) -> list[Book]:
    scraper = KindleScraper(headless=headless)
    books = await scraper.scrape_all_books(
        specific_asin=asin, output_path=output_path, resume=resume
    )

    if not resume and books:
        scraper.export_to_json(books, output_path)

    return books
