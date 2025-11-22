import pytest
from pathlib import Path
from kindle_highlights.parser import (
    parse_book_library,
    parse_annotations_html,
    parse_book_from_annotations_page,
    extract_color_from_classes,
    extract_page_location,
)


@pytest.fixture
def sample_html():
    """Load the sample Kindle notebook HTML fixture."""
    html_path = Path(__file__).parent / "fixtures" / "sample_notebook.html"
    return html_path.read_text(encoding="utf-8")


def test_extract_color_from_classes():
    """Test color extraction from CSS classes."""
    assert extract_color_from_classes(["kp-notebook-highlight-yellow"]) == "yellow"
    assert extract_color_from_classes(["kp-notebook-highlight-blue"]) == "blue"
    assert extract_color_from_classes(["kp-notebook-highlight-pink"]) == "pink"
    assert extract_color_from_classes(["kp-notebook-highlight-orange"]) == "orange"
    assert extract_color_from_classes(["some-other-class"]) == "yellow"  # default


def test_extract_page_location():
    """Test page and location extraction from text."""
    page, location = extract_page_location("Page 42 • Location 283")
    assert page == 42
    assert location == 283

    page, location = extract_page_location("Location 1500")
    assert page is None
    assert location == 1500

    page, location = extract_page_location("Page 10")
    assert page == 10
    assert location is None

    page, location = extract_page_location("No numbers here")
    assert page is None
    assert location is None


def test_parse_book_library(sample_html):
    """Test parsing the book library from HTML."""
    books = parse_book_library(sample_html)

    # Should find multiple books
    assert len(books) > 5

    # Check the first book (from the sample HTML)
    first_book = books[0]
    assert first_book["asin"] == "B00X57B4JG"
    assert "Why Greatness Cannot Be Planned" in first_book["title"]
    assert "Kenneth O. Stanley" in first_book["author"]
    assert first_book["cover_url"].startswith("https://m.media-amazon.com")


def test_parse_annotations_html(sample_html):
    """Test parsing highlights from annotations HTML."""
    highlights = parse_annotations_html(sample_html)

    # Should find multiple highlights
    assert len(highlights) >= 5

    # Check first highlight has required fields
    first_highlight = highlights[0]
    assert first_highlight.id
    assert first_highlight.text
    assert first_highlight.color in ["yellow", "blue", "pink", "orange"]

    # Check that we found meaningful text
    highlight_texts = [h.text for h in highlights]
    assert any("Charles Babbage" in text for text in highlight_texts)


def test_parse_book_from_annotations_page(sample_html):
    """Test parsing a complete book with metadata and highlights."""
    book = parse_book_from_annotations_page(sample_html)

    assert book is not None
    assert book.asin == "B00X57B4JG"
    assert "Why Greatness Cannot Be Planned" in book.title
    assert "Kenneth O. Stanley" in book.author
    assert book.cover_url.startswith("https://m.media-amazon.com")
    assert len(book.highlights) >= 5

    # Check that highlights have proper structure
    for highlight in book.highlights:
        assert highlight.id
        assert highlight.text
        assert highlight.color in ["yellow", "blue", "pink", "orange"]


def test_highlights_have_meaningful_content(sample_html):
    """Test that parsed highlights contain expected meaningful content."""
    highlights = parse_annotations_html(sample_html)

    # Should find specific content from the sample
    highlight_texts = [h.text.lower() for h in highlights]

    # Check for some expected content from the sample
    expected_keywords = ["babbage", "computer", "serendipitous", "objective"]
    found_keywords = []

    for keyword in expected_keywords:
        if any(keyword in text for text in highlight_texts):
            found_keywords.append(keyword)

    # Should find at least some of the expected content
    assert len(found_keywords) >= 2, f"Found keywords: {found_keywords}"


def test_empty_html_handling():
    """Test handling of empty or malformed HTML."""
    empty_highlights = parse_annotations_html("")
    assert empty_highlights == []

    empty_books = parse_book_library("")
    assert empty_books == []

    empty_book = parse_book_from_annotations_page("")
    assert empty_book is None
