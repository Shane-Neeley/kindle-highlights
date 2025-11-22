import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass
class Highlight:
    id: str
    color: str
    text: str
    page: int | None = None
    location: int | None = None
    note: str | None = None


@dataclass
class Book:
    asin: str
    title: str
    author: str
    cover_url: str
    highlights: list[Highlight]


def extract_color_from_classes(classes: list[str]) -> str:
    """Extract highlight color from CSS class names."""
    for cls in classes:
        if cls.endswith("-yellow"):
            return "yellow"
        elif cls.endswith("-blue"):
            return "blue"
        elif cls.endswith("-pink"):
            return "pink"
        elif cls.endswith("-orange"):
            return "orange"
    return "yellow"  # default


def extract_page_location(text: str) -> tuple[int | None, int | None]:
    """Extract page and location numbers from header text."""
    page, location = None, None

    # Look for "Page X" pattern
    page_match = re.search(r"Page (\d+)", text)
    if page_match:
        page = int(page_match.group(1))

    # Look for "Location X" pattern
    location_match = re.search(r"Location (\d+)", text)
    if location_match:
        location = int(location_match.group(1))

    return page, location


def parse_book_library(html: str) -> list[dict]:
    """Parse the book library from kp-notebook-library section."""
    soup = BeautifulSoup(html, "html.parser")
    books = []

    # First try to find the wrapper div
    library = soup.find("div", id="kp-notebook-library")
    if library:
        book_elements = library.find_all("div", class_="kp-notebook-library-each-book")
    else:
        # If no wrapper, assume we have the inner HTML directly
        book_elements = soup.find_all("div", class_="kp-notebook-library-each-book")

    for book_elem in book_elements:
        asin = book_elem.get("id", "")
        if not asin:
            continue

        # Extract title
        title_elem = book_elem.find("h2", class_="kp-notebook-searchable")
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract author
        author_elem = book_elem.find("p", class_="kp-notebook-searchable")
        author_text = author_elem.get_text(strip=True) if author_elem else ""
        author = author_text.replace("By: ", "") if author_text.startswith("By: ") else author_text

        # Extract cover URL
        img_elem = book_elem.find("img", class_="kp-notebook-cover-image")
        cover_url = img_elem.get("src", "") if img_elem else ""

        books.append({"asin": asin, "title": title, "author": author, "cover_url": cover_url})

    return books


def parse_annotations_html(html: str) -> list[Highlight]:
    """Parse highlights from annotations HTML."""
    soup = BeautifulSoup(html, "html.parser")
    highlights = []

    # Find the annotations container
    annotations_container = soup.find("div", id="kp-notebook-annotations")
    if not annotations_container:
        return highlights

    # Find all annotation blocks (each highlight is in its own div with an ID)
    annotation_blocks = annotations_container.find_all("div", id=True)

    for block in annotation_blocks:
        highlight_id = block.get("id", "")
        if not highlight_id:
            continue

        # Find the actual highlight element within this block
        highlight_elem = block.find("div", class_="kp-notebook-highlight")
        if not highlight_elem:
            continue

        # Extract color from CSS classes
        classes = highlight_elem.get("class", [])
        color = extract_color_from_classes(classes)

        # Extract highlight text
        text_elem = highlight_elem.find("span", class_="a-size-base-plus")
        text = text_elem.get_text(strip=True) if text_elem else ""

        # Extract page/location from header in the same block
        page, location = None, None
        header_elem = block.find("span", id="annotationHighlightHeader")
        if header_elem:
            page, location = extract_page_location(header_elem.get_text())

        # Look for location input field as backup
        if location is None:
            location_input = block.find("input", id="kp-annotation-location")
            if location_input and location_input.get("value"):
                try:
                    location = int(location_input.get("value"))
                except ValueError:
                    pass

        # Extract note if present
        note = None
        note_elem = block.find("div", class_="kp-notebook-note")
        if note_elem:
            note_text_elem = note_elem.find("span", class_="a-size-base-plus")
            if note_text_elem:
                note = note_text_elem.get_text(strip=True)

        if text and highlight_id:  # Only add if we have essential data
            highlights.append(
                Highlight(
                    id=highlight_id,
                    color=color,
                    text=text,
                    page=page,
                    location=location,
                    note=note,
                )
            )

    return highlights


def parse_book_from_annotations_page(html: str) -> Book | None:
    """Parse book metadata and highlights from a single book's annotations page."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract ASIN from hidden input
    asin_input = soup.find("input", id="kp-notebook-annotations-asin")
    asin = asin_input.get("value", "") if asin_input else ""

    # Extract book metadata from the header
    title_elem = soup.find("h3", class_="kp-notebook-metadata")
    title = title_elem.get_text(strip=True) if title_elem else ""

    # Author is in the p element after title (but not the first one which says "Your Kindle Notes For:")
    author = ""
    for p_elem in soup.find_all("p", class_="kp-notebook-metadata"):
        text = p_elem.get_text(strip=True)
        if (
            text
            and not text.startswith("Your Kindle Notes For:")
            and not text.startswith("Last accessed")
        ):
            author = text
            break

    # Cover URL from img
    cover_elem = soup.find("img", class_="kp-notebook-cover-image-border")
    cover_url = cover_elem.get("src", "") if cover_elem else ""

    # Parse highlights
    highlights = parse_annotations_html(html)

    if not asin or not title:
        return None

    return Book(
        asin=asin,
        title=title,
        author=author,
        cover_url=cover_url,
        highlights=highlights,
    )
