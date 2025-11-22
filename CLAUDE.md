# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python 3.12 tool that scrapes Kindle highlights from Amazon's notebook page using Playwright for browser automation and BeautifulSoup for HTML parsing.

## Quick Start Commands

**Setup:**
```bash
uv sync
uv run playwright install --with-deps chromium
cp .env.example .env  # Then edit with credentials
```

**Run scraper:**
```bash
# All books
uv run python -m kindle_highlights scrape

# Specific book
uv run python -m kindle_highlights scrape --asin B00X57B4JG

# Visible browser (debugging/manual 2FA)
uv run python -m kindle_highlights scrape --headful
```

**Testing:**
```bash
uv run pytest tests/ -v
# Note: Some tests require pageexample.html (not in repo)
```

## Architecture

### Module Structure

**`parser.py`** - HTML parsing and data models
- `Book` and `Highlight` dataclasses
- `parse_book_library(html)` - Extract books from library page
- `parse_annotations_html(html)` - Extract highlights (color, text, page, location, notes)
- `parse_book_from_annotations_page(html)` - Combine metadata + highlights

**`scraper.py`** - Playwright automation
- `KindleScraper` class handles full workflow:
  - **Authentication**: Email/password login, TOTP 2FA, session persistence (`playwright/.auth/user.json`)
  - **Discovery**: Infinite scroll to load all books
  - **Scraping**: Click book → scroll annotations → parse HTML
  - **Progressive saving**: Each book saved immediately with resume capability

**`__main__.py`** - CLI interface (argparse)

### Key Patterns

**Dynamic Content Loading**
- Infinite scroll: scroll → count elements → repeat until stable (3 checks)
- Applied to both library and individual book highlights

**Authentication Flow**
1. Navigate to notebook page
2. Check if logged in (`#kp-notebook-library` present)
3. Fill email → password → TOTP (if required)
4. Save session for reuse

**Resume Functionality**
- Default enabled: skips books already in output file
- Allows restart without reprocessing

### HTML Selectors

**Library page:**
- Container: `#kp-notebook-library`
- Books: `.kp-notebook-library-each-book`

**Annotations page:**
- Container: `#kp-notebook-annotations`
- Highlights: `.kp-notebook-highlight` with color classes (yellow/blue/pink/orange)
- Text: `.a-size-base-plus`
- Notes: `.kp-notebook-note`

## Important Notes

- **Amazon Passkeys**: Must be deleted before running (interferes with password login)
- **Export Limits**: Amazon may truncate highlights for some books (scraper warns)
- **Session Reset**: Delete `playwright/.auth/user.json` if login fails
- **Tests**: Only unit tests pass without `pageexample.html` sample file
