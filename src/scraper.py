from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
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


ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
AUTH_MODES = {"auto", "session", "interactive", "credentials"}
NOTEBOOK_URL = "https://read.amazon.com/notebook?ref_=kcr_notebook_lib&language=en-US"


def iso_timestamp() -> str:
    """Return an unambiguous UTC timestamp for export metadata."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_asin(asin: str) -> str:
    """Validate an ASIN before interpolating it into a CSS selector."""
    normalized = asin.strip().upper()
    if not ASIN_PATTERN.fullmatch(normalized):
        raise ValueError("ASIN must contain exactly 10 letters or digits")
    return normalized


def is_amazon_error_page(title: str) -> bool:
    """Recognize Amazon's generic pre-login failure page."""
    return title.strip().casefold() == "something went wrong"


class KindleScraper:
    def __init__(
        self,
        headless: bool = False,
        auth_mode: str = "auto",
        auth_state_path: str | Path = "playwright/.auth/user.json",
    ):
        load_dotenv()
        self.headless = headless
        if auth_mode not in AUTH_MODES:
            raise ValueError(f"Unknown authentication mode: {auth_mode}")
        if auth_mode == "interactive" and headless:
            raise ValueError("Interactive authentication requires a visible browser")

        self.auth_mode = auth_mode
        self.email: str | None = os.getenv("AMAZON_EMAIL")
        self.password: str | None = os.getenv("AMAZON_PASSWORD")
        self.totp_secret: str | None = os.getenv("AMAZON_TOTP_SECRET")
        self.auth_state_path = Path(auth_state_path)
        self.auth_state_path.parent.mkdir(parents=True, exist_ok=True)

        if auth_mode == "credentials" and not self.has_credentials:
            raise ValueError("Credential authentication requires AMAZON_EMAIL and AMAZON_PASSWORD")

    @property
    def has_credentials(self) -> bool:
        return bool(self.email and self.password)

    async def _wait_for_manual_sign_in(self, page: Page) -> bool:
        if self.headless:
            return False

        print("Complete the Amazon sign-in in the browser window.")
        print("The session will be saved locally for future runs.")
        try:
            await page.wait_for_selector("#kp-notebook-library", timeout=300000)
            return True
        except Exception as exc:  # pragma: no cover - user timing
            print(f"Manual sign-in did not complete: {exc}")
            return False

    async def authenticate(self, page: Page) -> bool:
        """Reuse a saved session, then authenticate using the selected fallback."""
        print("Navigating to Amazon Kindle notebook...")
        await page.goto(NOTEBOOK_URL)

        if is_amazon_error_page(await page.title()):
            print(
                "Amazon rejected the notebook request before sign-in. "
                "Refresh the saved session in the default visible browser mode."
            )
            return False

        # Wait for either login form or already logged in content
        login_or_library = (
            'input[name="email"]:not([type="hidden"]), '
            'input#ap_email:not([type="hidden"]), '
            'input#ap_email_login:not([type="hidden"]), '
            "#kp-notebook-library"
        )

        try:
            await page.wait_for_selector(login_or_library, timeout=20000)
        except Exception as e:  # pragma: no cover - network timing
            print(f"Page took too long to load: {e}")
            return False

        # Check if already logged in
        if await page.locator("#kp-notebook-library").count() > 0:
            print("Using saved Amazon session.")
            return True

        if self.auth_mode == "session":
            print("Saved Amazon session is missing or expired.")
            return False

        if self.auth_mode == "interactive" or not self.has_credentials:
            if self.headless:
                print(
                    "No valid saved session or credentials are available. "
                    "Run without --headless to sign in interactively."
                )
                return False
            return await self._wait_for_manual_sign_in(page)

        # Fill in email (or reuse claimed email if Amazon pre-selects account)
        email_input = page.locator(
            'input[name="email"]:not([type="hidden"]), '
            'input#ap_email:not([type="hidden"]), '
            'input#ap_email_login:not([type="hidden"])'
        )
        if await email_input.count() > 0:
            print("Entering email...")
            await email_input.first.fill(cast(str, self.email))
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
            await password_input.first.fill(cast(str, self.password))
            await page.click('input[type="submit"], input#signInSubmit')
            await page.wait_for_timeout(3000)

        # Handle TOTP if required
        totp_input = page.locator('input[name="otpCode"]')
        if await totp_input.count() > 0:
            if self.totp_secret:
                totp = pyotp.TOTP(self.totp_secret)
                code = totp.now()
                print("Entering TOTP code...")
                await totp_input.fill(code)
                await page.click('input[type="submit"]')
                await page.wait_for_timeout(3000)
            else:
                print("TOTP required but AMAZON_TOTP_SECRET not set.")
                return await self._wait_for_manual_sign_in(page)

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
            raise RuntimeError(
                "Could not find the Kindle library. Amazon may have changed the page "
                "or returned an incomplete response. Authenticated page HTML was not "
                "saved because it may contain private data."
            )

        library_html = await library_element.inner_html()
        parsed_books = parse_book_library(library_html)
        books: list[dict[str, str]] = []
        for book in parsed_books:
            try:
                book["asin"] = validate_asin(book["asin"])
            except (KeyError, ValueError) as exc:
                raise RuntimeError("Kindle library contains a malformed book entry") from exc
            books.append(book)

        if not books:
            raise RuntimeError("Kindle library is empty; refusing an incomplete export")

        print(f"Total books found: {len(books)}")
        return books

    async def scrape_book_highlights(self, page: Page, asin: str) -> Book:
        """Scrape highlights for a specific book."""
        asin = validate_asin(asin)
        print(f"Scraping highlights for book {asin}...")

        book_link = page.locator(f"#kp-notebook-library #{asin} a")
        await book_link.click()

        try:
            await page.wait_for_selector("#kp-notebook-annotations", timeout=10000)
        except Exception as exc:  # pragma: no cover - network timing
            raise RuntimeError(f"Failed to load annotations for book {asin}") from exc

        metadata_text = await page.locator(".kp-notebook-metadata").all_text_contents()
        expected_count = next(
            (
                int(match.group(1).replace(",", ""))
                for text in metadata_text[:5]
                if (match := re.search(r"([\d,]+)\s+Highlights?", text, flags=re.IGNORECASE))
            ),
            None,
        )

        last_count = -1
        stable_count = 0

        while stable_count < 3:
            await page.evaluate(
                "document.querySelector('#annotation-scroller').scrollTo(0, document.querySelector('#annotation-scroller').scrollHeight)"
            )
            await page.wait_for_timeout(2000)

            current_count = await page.locator(
                "#kp-notebook-annotations .kp-notebook-highlight"
            ).count()

            if expected_count is not None and current_count >= expected_count:
                break

            if current_count == last_count:
                stable_count += 1
            else:
                stable_count = 0
                last_count = current_count

        truncation_banner = page.locator("#kp-notebook-hidden-annotations-summary")
        if await truncation_banner.count() > 0:
            raise RuntimeError(f"Highlights for book {asin} are truncated by Amazon")

        if expected_count is not None and current_count < expected_count:
            raise RuntimeError(
                f"Incomplete highlights for book {asin}: expected {expected_count}, "
                f"received {current_count}"
            )

        page_html = await page.content()
        book = parse_book_from_annotations_page(page_html)

        if book is None:
            raise RuntimeError(f"Could not parse annotations for book {asin}")
        if expected_count is not None and len(book.highlights) < expected_count:
            raise RuntimeError(f"Parsed fewer highlights than Amazon reports for book {asin}")

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
                try:
                    context = await browser.new_context(storage_state=str(self.auth_state_path))
                except Exception as exc:
                    # A partial write or old Playwright version can make storage
                    # state unreadable. Fall back without deleting forensic data.
                    print(f"Saved browser session could not be loaded: {exc}")
                    context = await browser.new_context()
            else:
                context = await browser.new_context()

            page = await context.new_page()

            try:
                if not await self.authenticate(page):
                    raise RuntimeError("Authentication failed")

                await context.storage_state(path=str(self.auth_state_path))
                self.auth_state_path.chmod(0o600)

                books: list[Book] = []

                if specific_asin:
                    book = await self.scrape_book_highlights(page, specific_asin)
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
                        books.append(book)
                        self.save_book_progressively(book, output_path)

                        processed_count += 1
                        print(f"Progress: {processed_count}/{total_books} books processed")

                return books

            finally:
                await browser.close()

    def _empty_export_data(self) -> ExportData:
        return {"run": {"timestamp": iso_timestamp()}, "books": []}

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

        if (
            not isinstance(data, dict)
            or not isinstance(data.get("run"), dict)
            or not isinstance(data.get("books"), list)
        ):
            print(f"Warning: Existing file {output_path} has an invalid export structure")
            return self._empty_export_data()

        return cast(ExportData, data)

    def get_existing_book_asins(self, data: ExportData) -> set[str]:
        """Get set of ASINs that already exist in the data."""
        asins: set[str] = set()
        for book in data.get("books", []):
            if not isinstance(book, dict):
                continue
            asin = book.get("asin")
            if isinstance(asin, str):
                try:
                    asins.add(validate_asin(asin))
                except ValueError:
                    continue
        return asins

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

        data["run"]["timestamp"] = iso_timestamp()

        self._atomic_write_json(data, output_path)

    def export_to_json(self, books: list[Book], output_path: str) -> None:
        """Export scraped books to JSON file (batch mode - kept for compatibility)."""
        data: ExportData = self._empty_export_data()
        data["books"] = []

        for book in books:
            book_data = self.book_to_dict(book)
            data["books"].append(book_data)

        self._atomic_write_json(data, output_path)

        print(f"Exported {len(books)} books to {output_path}")

    def _atomic_write_json(self, data: ExportData, output_path: str) -> None:
        """Write personal export data atomically with owner-only permissions."""
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as file_handle:
                temporary = Path(file_handle.name)
                json.dump(data, file_handle, indent=2, ensure_ascii=False)
                file_handle.flush()
                os.fsync(file_handle.fileno())
            temporary.chmod(0o600)
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


async def scrape_kindle_highlights(
    output_path: str,
    asin: str | None = None,
    headless: bool = False,
    resume: bool = False,
    auth_mode: str = "auto",
) -> list[Book]:
    normalized_asin = validate_asin(asin) if asin else None
    scraper = KindleScraper(headless=headless, auth_mode=auth_mode)
    books = await scraper.scrape_all_books(
        specific_asin=normalized_asin, output_path=output_path, resume=resume
    )

    # A single-book refresh must update that book in the existing export, not
    # replace the user's complete library with one title.
    if not resume and not normalized_asin and books:
        scraper.export_to_json(books, output_path)

    return books
