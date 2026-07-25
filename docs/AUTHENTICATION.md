# Authentication methods

Kindle Highlights uses Amazon’s normal notebook website. Amazon does not expose
a supported public API for bulk highlight export, so every acquisition method
ultimately needs an authenticated browser session.

## Recommended default: interactive session bootstrap

```bash
uv run kindle-highlights scrape
```

The scraper opens its own visible Chromium window. Complete Amazon sign-in,
including passkey, security-key, CAPTCHA, or 2FA steps, in that window. After
the notebook appears, Playwright saves browser storage state to:

```text
playwright/.auth/user.json
```

Future runs try this saved session first. The file is gitignored and written
with owner-only permissions (`0600`), but it still contains sensitive session
material. Anyone who obtains it may be able to access the Amazon account.

## Headless saved-session reuse

After interactive bootstrap:

```bash
uv run kindle-highlights scrape --headless
```

This is suitable for local schedulers while the session remains valid. If
Amazon expires or challenges the session, rerun in visible mode.

To require a valid saved session and forbid fallback:

```bash
uv run kindle-highlights scrape --headless --auth session
```

## Optional unattended credentials

For environments where interactive session refresh is impossible, copy
`.env.example` to `.env` and set `AMAZON_EMAIL` and `AMAZON_PASSWORD`.
`AMAZON_TOTP_SECRET` can automate authenticator-code challenges.

```bash
uv run kindle-highlights scrape --headless --auth credentials
```

This mode is less desirable because it stores reusable account credentials.
Never commit `.env`, print TOTP values, or bake credentials into a container
image. Amazon may still require an interactive challenge.

## Explicit interactive mode

```bash
uv run kindle-highlights scrape --auth interactive
```

This ignores configured credentials after trying any saved session. It is
useful when passkeys or manual approval are preferred.

## Why not attach to everyday Chrome?

Attaching automation to a daily browser profile can reuse an existing login,
but it also gives the scraper access to unrelated tabs, cookies, and extension
state. Browser profiles may be locked while Chrome is running, and profile
formats change across Chrome versions. A dedicated Playwright session has a
smaller security boundary and is reproducible across platforms, so it remains
the project default.

## Why not scrape exported HTML?

Saving the notebook page as HTML is useful for parser fixtures and debugging,
but Kindle loads books and annotations dynamically. A saved page often
contains only the currently rendered subset, making silent data loss likely.
The live browser workflow verifies that lazy-loaded counts stabilize before
parsing and is therefore the authoritative acquisition method.

## Rotating session state

Delete `playwright/.auth/user.json` to force a new sign-in. Also revoke Amazon
sessions from the account security page if the file may have been exposed.
