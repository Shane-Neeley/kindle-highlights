# Security

## Sensitive local files

This public repository must never contain:

- `.env` or Amazon credentials
- `playwright/.auth/user.json` or other browser storage state
- real `data/*.json` highlight exports
- raw authenticated notebook HTML

These paths are gitignored. Export and session files are written with
owner-only permissions where the operating system supports POSIX modes.
Treat both as account or personal-data secrets even though they are plain
files.

## Service API

Run the service on loopback unless a trusted reverse proxy provides
authentication:

```bash
uv run uvicorn app:app --host 127.0.0.1 --port 8000 --app-dir src
```

`GET /books` and `GET /highlights` expose the cached reading data. They do not
have application-level authentication.

`POST /scrape` launches browser automation and modifies the export. It is
disabled until `KINDLE_SCRAPE_API_TOKEN` is configured and then requires:

```http
Authorization: Bearer <KINDLE_SCRAPE_API_TOKEN>
```

Generate a long random value rather than reusing an Amazon password:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

## Reporting vulnerabilities

Please report security issues privately through GitHub’s security-advisory
interface. Do not open a public issue containing credentials, session state,
private highlights, or a working exploit against an Amazon account.
