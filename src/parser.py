from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import TypedDict

from bs4 import BeautifulSoup
from bs4.element import Tag


class HighlightData(TypedDict):
    id: str
    text: str
    color: str
    page: int | None
    location: int | None
    note: str | None


@dataclass
class Highlight:
    id: str
    text: str
    color: str
    page: int | None
    location: int | None
    note: str | None


@dataclass
class Book:
    asin: str
    title: str
    author: str
    cover_url: str
    highlights: list[Highlight]


def parse_book_library(html_content: str) -> list[dict[str, str]]:
    """Parse the book library page to extract book metadata."""
    soup = BeautifulSoup(html_content, "html.parser")
    books: list[dict[str, str]] = []

    book_elements = soup.select(".kp-notebook-library-each-book")

    for book_element in book_elements:
        asin = str(book_element.get("id", ""))
        searchables = book_element.select(".kp-notebook-searchable")
        title = html.unescape(searchables[0].get_text(strip=True)) if searchables else ""

        author = ""
        if len(searchables) > 1:
            raw_author = searchables[1].get_text(strip=True)
            author = html.unescape(raw_author.removeprefix("By:").strip())

        cover_element = book_element.select_one("img")
        cover_url = str(cover_element.get("src", "")) if cover_element else ""

        books.append(
            {
                "asin": asin,
                "title": title,
                "author": author,
                "cover_url": cover_url,
            }
        )

    return books


def extract_color_from_classes(classes: list[str]) -> str:
    """Extract highlight color from CSS classes."""
    color_map = {
        "kp-notebook-highlight-yellow": "yellow",
        "kp-notebook-highlight-blue": "blue",
        "kp-notebook-highlight-pink": "pink",
        "kp-notebook-highlight-orange": "orange",
    }

    for class_name in classes:
        if class_name in color_map:
            return color_map[class_name]

    return "yellow"  # Default color


def extract_page_location(text: str) -> tuple[int | None, int | None]:
    """Extract page and location numbers from text."""
    # Kindle formats large values with thousands separators (for example
    # "Location 1,305"). Accept both formats and normalize them to integers.
    page_match = re.search(r"Page\s+([\d,]+)", text, flags=re.IGNORECASE)
    location_match = re.search(r"Location:?\s+([\d,]+)", text, flags=re.IGNORECASE)

    page = int(page_match.group(1).replace(",", "")) if page_match else None
    location = int(location_match.group(1).replace(",", "")) if location_match else None

    return page, location


def parse_annotations_html(html_content: str) -> list[Highlight]:
    """Parse the annotations list HTML to extract highlights."""
    soup = BeautifulSoup(html_content, "html.parser")
    highlights: list[Highlight] = []

    highlight_elements = soup.select("#kp-notebook-annotations .kp-notebook-highlight")

    for element in highlight_elements:
        highlight_id = str(element.get("id", ""))
        if not highlight_id:
            parent_with_id = element.find_parent(id=True)
            highlight_id = (
                str(parent_with_id.get("id", "")) if isinstance(parent_with_id, Tag) else ""
            )

        text_element = element.select_one(".a-size-base-plus") or element
        text = html.unescape(text_element.get_text(strip=True))

        classes = element.get("class")
        if not isinstance(classes, list):
            classes = []
        color = extract_color_from_classes(classes)

        header_element = element.find_previous("span", id="annotationHighlightHeader")
        page, location = extract_page_location(
            header_element.get_text(strip=True) if header_element else ""
        )

        note_element = element.find_next_sibling("div", class_="kp-notebook-note")
        note_span = (
            note_element.select_one(".a-size-base-plus") if isinstance(note_element, Tag) else None
        )
        note = html.unescape(note_span.get_text(strip=True)) if note_span else None

        highlights.append(Highlight(highlight_id, text, color, page, location, note))

    return highlights


def parse_book_from_annotations_page(html_content: str) -> Book | None:
    """Parse the book info and annotations from a loaded book page."""
    soup = BeautifulSoup(html_content, "html.parser")

    book_title_element = soup.select_one("h3.kp-notebook-metadata")
    author_elements = soup.select(".kp-notebook-metadata")

    if not book_title_element or len(author_elements) < 3:
        return None

    book_title = html.unescape(book_title_element.get_text(strip=True))
    author = html.unescape(author_elements[2].get_text(strip=True))

    cover_element = soup.select_one("#annotation-scroller .kp-notebook-cover-image-border")
    if cover_element is None:
        cover_element = soup.select_one(".kp-notebook-cover-image-border")
    cover_url = str(cover_element.get("src", "")) if cover_element else ""

    asin_input = soup.select_one("#kp-notebook-annotations-asin, #kp-notebook-asin")
    asin = str(asin_input.get("value", "")) if asin_input else ""
    if not asin:
        product_link = soup.select_one('a.kp-notebook-printable[href*="/dp/"]')
        if product_link:
            asin = str(product_link.get("href", "")).split("/dp/")[-1].split("?")[0]

    highlights = parse_annotations_html(html_content)

    return Book(asin, book_title, author, cover_url, highlights)
