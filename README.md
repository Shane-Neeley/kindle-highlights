# Kindle Highlights Scraper

Export all your Kindle highlights from Amazon's notebook page to structured JSON.

> **Note:** You must disable/delete Amazon passkey authentication if enabled, as it interferes with password-based login.

## Features

- ✨ Scrape all highlights from your entire Kindle library
- 🔐 Secure authentication with 2FA/TOTP support
- 💾 Progressive saving with resume capability
- 🎨 Preserves highlight colors and notes
- 📍 Captures page numbers and locations
- 🔄 Session persistence (no repeated logins)

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone repository
git clone <repo-url>
cd kindle-highlights

# Install dependencies
uv sync

# Install browser
uv run playwright install --with-deps chromium

# Configure credentials
cp .env.example .env
```

Edit `.env` with your Amazon credentials:
```env
AMAZON_EMAIL=your-email@example.com
AMAZON_PASSWORD=your-password
AMAZON_TOTP_SECRET=your-totp-secret  # Optional, for 2FA
```

### Usage

**Scrape all books:**
```bash
uv run python -m kindle_highlights scrape
```

**Scrape specific book:**
```bash
uv run python -m kindle_highlights scrape --asin B00X57B4JG
```

**Custom output location:**
```bash
uv run python -m kindle_highlights scrape --out my-highlights.json
```

**Manual 2FA (visible browser):**
```bash
uv run python -m kindle_highlights scrape --headful
```

## Output Format

```json
{
  "run": {
    "timestamp": "2025-11-22T12:34:56Z"
  },
  "books": [
    {
      "asin": "B00X57B4JG",
      "title": "Why Greatness Cannot Be Planned",
      "author": "Kenneth O. Stanley; Joel Lehman",
      "cover_url": "https://...",
      "highlights": [
        {
          "id": "highlight-abc123",
          "color": "yellow",
          "text": "The highlight text...",
          "page": 42,
          "location": 283,
          "note": "Optional note..."
        }
      ]
    }
  ]
}
```

## How It Works

1. **Authenticate** - Logs into Amazon with Playwright (headless browser)
2. **Discover** - Scrolls through library to find all annotated books
3. **Extract** - For each book, loads and scrolls annotations to get all highlights
4. **Parse** - BeautifulSoup extracts structured data from HTML
5. **Save** - Progressively saves each book to JSON (enables resume)

## Resume Capability

By default, scraping resumes from where it left off. Already-processed books are skipped:

```bash
# Interrupted? Just run again - it continues from where it stopped
uv run python -m kindle_highlights scrape

# Need a clean export? Disable resume to reprocess every book
uv run python -m kindle_highlights scrape --fresh
```

## Testing

```bash
# Run test suite
uv run pytest tests/ -v

# Run specific tests
uv run pytest tests/test_parser.py -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Login fails** | Delete `playwright/.auth/user.json` and try again |
| **2FA required** | Add `AMAZON_TOTP_SECRET` to `.env` or use `--headful` mode |
| **Passkey blocking** | Disable/delete Amazon passkey in your account settings |
| **Missing highlights** | Some books have Amazon export limits (scraper will warn) |
| **Browser executable missing (Playwright install message)** | Run `uv run playwright install --with-deps chromium` to download Chromium, then retry the scrape |
| **General browser issues** | Reinstall: `uv run playwright install --with-deps chromium` |

## Project Structure

```
kindle_highlights/
├── parser.py          # HTML parsing with BeautifulSoup
├── scraper.py         # Browser automation with Playwright
└── __main__.py        # CLI interface
tests/
└── test_parser.py     # Unit tests
```

## Configuration

### Environment Variables

- `AMAZON_EMAIL` (required) - Your Amazon account email
- `AMAZON_PASSWORD` (required) - Your Amazon account password
- `AMAZON_TOTP_SECRET` (optional) - Base32 TOTP secret for 2FA

### Getting TOTP Secret

If you use authenticator apps for 2FA, the TOTP secret is the base32 key shown when you set up the authenticator. Save it during initial 2FA setup to enable automated authentication.

## Limitations

- **Amazon passkeys** must be disabled (password-based login required)
- **Export limits** - Amazon may restrict highlights for some books
- **Session cookies** - Stored in `playwright/.auth/user.json` (gitignored)
- **Rate limiting** - Uses 2-second delays to be respectful to Amazon's servers

## License

See LICENSE file for details.

## Contributing

- Read `AGENTS.md` for repository-wide coding standards, commit expectations, and security reminders before opening a PR.
- Run `uv run pytest -v` plus at least one dry scrape (`uv run python -m kindle_highlights scrape --headful` when debugging selectors) to validate DOM changes.
- Sanitize or delete `data/highlights.json` when sharing logs; never include `.env` or Playwright auth files in commits.

## Acknowledgments

Built with [Playwright](https://playwright.dev/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/).
