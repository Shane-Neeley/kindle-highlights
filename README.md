# Kindle Highlights Scraper

Export all your Kindle highlights from Amazon's notebook page to structured JSON.

For the incremental weekly Chrome refresh, private checkpoints/backups and
highlights-only Firebase publishing, see [Weekly workflow](docs/WEEKLY.md).
The notebook URL is now `https://read.amazon.com/notebook`; the old `/kp/notebook`
route is retired. The signed-in Chrome workflow currently works while the separate
Playwright browser receives Amazon's generic pre-login error.

## Features

- ✨ Scrape all highlights from your entire Kindle library
- 🔐 Session-first authentication; no stored Amazon password required
- 🪟 Interactive sign-in supports passkeys and manual 2FA
- 🤖 Optional credentials/TOTP mode for unattended environments
- 💾 Progressive saving with resume capability
- 🛡️ Atomic private exports and a protected scrape API
- 🎨 Preserves highlight colors and notes
- 📍 Captures page numbers and locations
- 🔄 Session persistence (no repeated logins)

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

`brew install uv`

### Python & Dependency Compatibility

- `requires-python >= 3.13` (see `pyproject.toml`), verified locally on CPython 3.14.3 via uv.
- Playwright installs its browser separately from Python, so use the documented `uv run playwright install --with-deps chromium` step after dependency installation.
- `beautifulsoup4`, `python-dotenv`, and `pyotp` publish universal wheels with no CPython ABI constraints, so upgrading to 3.13 is safe without pin changes.

### Installation

```bash
# Clone repository
git clone https://github.com/Shane-Neeley/kindle-highlights.git
cd kindle-highlights

# Install dependencies
uv sync

# Install the project browser
uv run playwright install --with-deps chromium

# Run with a visible browser and sign in when prompted
uv run kindle-highlights scrape
```

The first successful sign-in is saved in `playwright/.auth/user.json`. Later
runs reuse that local session before attempting another authentication method.
See [Authentication methods](docs/AUTHENTICATION.md) for passkey, headless, and
unattended options.

### Usage

**Scrape all books:**

```bash
uv run kindle-highlights scrape
```

Every current book is refreshed by default so edited or deleted annotations
are reflected in the export.

**Scrape specific book:**

```bash
uv run kindle-highlights scrape --asin B00X57B4JG
```

**Custom output location:**

```bash
uv run kindle-highlights scrape --out my-highlights.json
```

**Resume an interrupted initial export:**

```bash
uv run kindle-highlights scrape --resume
```

`--resume` skips ASINs already in the output. It is fast, but does not detect
changed highlights in those books.

**Unattended run using a saved session or optional credentials:**

```bash
uv run kindle-highlights scrape --headless
```

### Service API

Run the FastAPI service locally (reload for development):

```bash
uv run uvicorn app:app --host 127.0.0.1 --port 8000 --app-dir src --reload
```

Endpoints:

- `GET /health` — service heartbeat + output path
- `GET /books` — cached export payload
- `GET /highlights` — flattened highlight list with book metadata
- `POST /scrape` — trigger a full refresh; set `fresh` to `false` only to resume
  an interrupted export

`HIGHLIGHTS_PATH` (optional) overrides where the API reads/writes the export file (default `data/highlights.json`).

`POST /scrape` is disabled unless `KINDLE_SCRAPE_API_TOKEN` is configured.
Send it as `Authorization: Bearer <token>`. This endpoint launches a browser
and modifies local data, so never expose it anonymously. The read endpoints
can also reveal personal notes; keep the service on loopback or protect it at
your reverse proxy.

### Docker

Build and run the service in a container:

```bash
docker build -t kindle-highlights .
docker run --rm -p 8000:8000 --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/playwright:/app/playwright \
  kindle-highlights
```

Mounting `data/` persists exports, and mounting `playwright/` keeps the cached Amazon auth state (`.auth/user.json`) between runs. Set `KINDLE_SCRAPE_API_TOKEN` in `.env` before using `POST /scrape`.

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

1. **Authenticate** - Reuses local session state or opens an interactive Playwright browser
2. **Discover** - Scrolls through library to find all annotated books
3. **Extract** - For each book, loads and scrolls annotations to get all highlights
4. **Parse** - BeautifulSoup extracts structured data from HTML
5. **Save** - Progressively saves each book to JSON (enables resume)

## Refresh and Resume

By default, scraping refreshes the full current library. This is necessary
because Kindle highlights can change after the first export.

```bash
# Interrupted during a large initial export? Skip completed ASINs
uv run kindle-highlights scrape --resume

# Explicit spelling for the default full refresh
uv run kindle-highlights scrape --fresh
```

Progress is saved after every book using atomic file replacement, so a crash
cannot leave a partially written JSON document.

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
| **Saved login fails**                                       | Run the default visible mode and sign in again; delete `playwright/.auth/user.json` only if needed |
| **2FA/passkey required**                                    | Complete it in the visible browser; the resulting session is saved locally                       |
| **Headless login fails**                                    | Refresh the session interactively first, or configure optional `.env` credentials                 |
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

- `AMAZON_EMAIL` (optional) - Email for unattended credential authentication
- `AMAZON_PASSWORD` (optional) - Password for unattended credential authentication
- `AMAZON_TOTP_SECRET` (optional) - Base32 TOTP secret for unattended 2FA
- `HIGHLIGHTS_PATH` (optional) - Override where the API reads/writes the export JSON
- `KINDLE_SCRAPE_API_TOKEN` (required for `POST /scrape`) - Long random bearer token

### Choosing an authentication method

Interactive sign-in is the default and supports Amazon’s current
authentication UI without storing account credentials. Use credential/TOTP
automation only when a human cannot refresh the saved session. See
[docs/AUTHENTICATION.md](docs/AUTHENTICATION.md).

## Limitations

- **Export limits** - Amazon may restrict highlights for some books
- **Session cookies** - Stored locally in `playwright/.auth/user.json` (gitignored, mode `0600`)
- **Rate limiting** - Uses 2-second delays to be respectful to Amazon's servers

## License

See LICENSE file for details.

## Contributing

- Read `AGENTS.md` for repository-wide coding standards, commit expectations, and security reminders before opening a PR.
- Run `uv run pytest -v`, `uv run ruff check`, and `ty check src tests` plus at least one dry scrape (`uv run kindle-highlights scrape --headful` when debugging selectors) to validate DOM changes.
- Sanitize or delete `data/highlights.json` when sharing logs; never include `.env` or Playwright auth files in commits.
- Read [SECURITY.md](SECURITY.md) before deploying the service API.
- Keep the `pre-commit` hooks enabled so Ruff and Ty run automatically before each commit.

## Acknowledgments

Built with [Playwright](https://playwright.dev/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/).
