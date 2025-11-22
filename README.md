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

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

`brew install uv`

### Python & Dependency Compatibility

- `requires-python >= 3.13` (see `pyproject.toml`), tested locally on CPython 3.13.6 via uv.
- Playwright’s [Python docs](https://playwright.dev/python/docs/intro) list support through Python 3.13, so `playwright>=1.40.0` remains valid on the latest interpreter.
- `beautifulsoup4`, `python-dotenv`, and `pyotp` publish universal wheels with no CPython ABI constraints, so upgrading to 3.13 is safe without pin changes.

### Installation

```bash
# Clone repository
git clone https://github.com/Shane-Neeley/kindle-highlights.git
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
uv run kindle-highlights scrape --headful
```

**Scrape specific book:**

```bash
uv run kindle-highlights scrape --asin B00X57B4JG
```

**Custom output location:**

```bash
uv run kindle-highlights scrape --out my-highlights.json
```

**Manual 2FA (visible browser):**

```bash
uv run kindle-highlights scrape --headful
```

### Service API

Run the FastAPI service locally (reload for development):

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --app-dir src --reload
```

Endpoints:

- `GET /health` — service heartbeat + output path
- `GET /books` — cached export payload
- `GET /highlights` — flattened highlight list with book metadata
- `POST /scrape` — trigger a scrape (`{"asin": "<ASIN>", "fresh": true}` to rescrape all)

`HIGHLIGHTS_PATH` (optional) overrides where the API reads/writes the export file (default `data/highlights.json`).

### Docker

Build and run the service in a container:

```bash
docker build -t kindle-highlights .
docker run --rm -p 8000:8000 --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/playwright:/app/playwright \
  kindle-highlights
```

Mounting `data/` persists exports, and mounting `playwright/` keeps the cached Amazon auth state (`.auth/user.json`) between runs.

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
uv run kindle-highlights scrape

# Need a clean export? Disable resume to reprocess every book
uv run kindle-highlights scrape --fresh
```

## Testing

```bash
# Run test suite
uv run pytest tests/ -v

# Run specific tests
uv run pytest tests/test_parser.py -v
```

## Quality Checks

```bash
# Format with Ruff
uv run ruff format

# Lint (pycodestyle/pyflakes/async rules/etc.)
uv run ruff check src tests

# Static analysis (Ty)
ty check src tests

# Packaging smoke test
uv build
```

Install `pre-commit` once (`uv tool install pre-commit`) and Ty’s CLI (`uv tool install ty`), then enable the hooks:

```bash
pre-commit install
pre-commit run --all-files
```

Ty is currently in early access; see https://docs.astral.sh/ty/ for the latest usage notes.
This repository is public. Please keep personal work artifacts (notes, scratch output, etc.) inside `docs/scratchpad/` so they stay out of version control; the directory is gitignored for that purpose.

## Troubleshooting

| Issue                                                       | Solution                                                                                         |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Login fails**                                             | Delete `playwright/.auth/user.json` and try again                                                |
| **2FA required**                                            | Add `AMAZON_TOTP_SECRET` to `.env` or use `--headful` mode                                       |
| **Passkey blocking**                                        | Disable/delete Amazon passkey in your account settings                                           |
| **Missing highlights**                                      | Some books have Amazon export limits (scraper will warn)                                         |
| **Browser executable missing (Playwright install message)** | Run `uv run playwright install --with-deps chromium` to download Chromium, then retry the scrape |
| **General browser issues**                                  | Reinstall: `uv run playwright install --with-deps chromium`                                      |

## Project Structure

```
src/
├── parser.py    # HTML parsing with BeautifulSoup
├── scraper.py   # Browser automation with Playwright
├── main.py      # CLI interface (argparse)
└── app.py       # FastAPI app for HTTP access
tests/
├── test_parser.py  # Unit tests
└── test_api.py     # FastAPI route tests
Dockerfile          # Containerized service runner
```

## Configuration

### Environment Variables

- `AMAZON_EMAIL` (required) - Your Amazon account email
- `AMAZON_PASSWORD` (required) - Your Amazon account password
- `AMAZON_TOTP_SECRET` (optional) - Base32 TOTP secret for 2FA
- `HIGHLIGHTS_PATH` (optional) - Override where the API reads/writes the export JSON

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
- Run `uv run pytest -v`, `uv run ruff check`, and `ty check src tests` plus at least one dry scrape (`uv run kindle-highlights scrape --headful` when debugging selectors) to validate DOM changes.
- Sanitize or delete `data/highlights.json` when sharing logs; never include `.env` or Playwright auth files in commits.
- Keep the `pre-commit` hooks enabled so Ruff and Ty run automatically before each commit.

## Acknowledgments

Built with [Playwright](https://playwright.dev/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/).
