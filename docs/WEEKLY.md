# Weekly Kindle refresh

The active Codex heartbeat is **Refresh Kindle highlights on shaneneeley.com**, Sunday
08:00 America/Los_Angeles. This Mac, Codex and the Shane Chrome profile's Codex
browser extension must be available. A signed-out notebook needs human sign-in.
The schedule is agent-driven; it is not a headless cron scraping every book.

## Reliable primary path

Use the already signed-in Shane Chrome profile (shane.neeley@gmail.com) and
https://read.amazon.com/notebook via `cua_repl`. Discover the profile at run time;
do not hard-code browser IDs. Do not read/copy cookies or Chrome profile files.

1. Preserve `data/highlights.json` as the baseline. If absent, seed it from
   `../shanesite/public/files/highlights.json`. Compare it with live data to reconcile
   any previous successful release whose local copy failed. Never seed from an empty file.
2. Read `scripts/chrome-capture.js` with file tools and paste its helpers into
   `cua_repl` after binding the notebook tab. These helpers use only documented
   browser/UI APIs. Inspect the current DOM to verify selectors before using them.
   `let library = await readLibrary(tab)` captures the rendered inventory only.
   Scroll the library with UI actions until book count is stable; require a nonempty
   inventory and investigate unexpected count drops. Never infer deleted books.
3. Start a new capture `{library,books:[],counts:{},captured_at:new Date().toISOString()}`.
   Persist this JSON in a **plain text** TextEdit document at
   `data/chrome-capture.txt` using native `cua` actions. Use File > New, Make Plain
   Text, paste the JSON, Save, and the local directory via Cmd+Shift+G. TextEdit can
   append `.txt`; confirm the actual path, then `chmod 600 data/chrome-capture.txt`.
   The directory and all captures/backups are private and gitignored.
4. Run from the scraper checkout:
   ```sh
   uv run python src/refresh.py plan --baseline data/highlights.json --capture data/chrome-capture.txt
   ```
   Refresh the returned ASINs only: all new books, the 20 most recently accessed,
   books that moved forward in the inventory, and 20 least recently checked older
   books. Every older book eventually gets audited even if its count stays constant.
   Amazon's access order is a heuristic, not a last-modified API: old-book edits
   can wait for rotation (about 13 weeks with today's library). A deliberate full
   audit may capture all ASINs instead; the same merge validates it.
5. Use `await captureBook(tab, info, capture)` for each planned book. Process batches
   of at most 10, with `timeout_ms:60000`, and call `checkpoint(editor,capture)`
   after each batch. Print counts only. Before reusing a same-day checkpoint after
   interruption, verify inventory, capture age and remaining ASINs; skip only those
   already validated in this run, never every book in the baseline.
   The helper checks product-link ASIN, title and reported highlight count.
   If incomplete, scroll the **annotation pane** with UI actions, re-read with
   `readBook(tab)` and verify the complete count before adding the book. Never
   publish a truncated/mismatched capture. Stop on auth/CAPTCHA/unknown DOM; no
   repeated requests or credential handling. Existing data stays intact.
6. Merge after the entire plan is present:
   ```sh
   uv run python src/refresh.py merge --baseline data/highlights.json --capture data/chrome-capture.txt
   ```
   Merge validates counts, ASINs, unique IDs, fresh capture (<24 hours) and plan
   coverage, backs up the baseline by content hash, atomically saves the result,
   and updates `data/refresh-state.json`. It preserves absent books and ignores
   timestamps/object ordering when deciding whether content changed.
   The Chrome helper also captures each selected book's visible Last accessed
   date in `capture.access_dates`, separately from the public highlights schema.
   Before merging, retain a private `data/prior-week.json` copy of the baseline.
   After **every successful merge**, including unchanged content, run:
   ```sh
   uv run python src/personal_reading.py --baseline data/prior-week.json
   ```
   This saves the complete export, capture and dated evidence packet privately at
   `~/skn/shane-neeley/personal-kb/reading/`, with immutable dated snapshots and
   a current seven-day packet. Use the actual local capture date (an explicit
   `--as-of YYYY-MM-DD` is only for historical replay). Preserve all history.
   Missing dates mean no dated reading claim; archive the full export anyway.
   If saving the private archive fails, report it instead of claiming the weekly
   workflow complete. Do not publish the personal packet or personal VOICE.md.
   `~/VOICE.md` points to this packet for the optional `shane-personal-voice` skill.
   Consider only relevant fresh evidence; do not rewrite stable taste weekly.
7. Validate and publish only when live content differs:
   ```sh
   uv run pytest -q
   uv run ruff check src tests/test_refresh.py
   node --test tests/publish-highlights.test.cjs
   node scripts/publish-highlights.cjs data/highlights.json
   ```
   If changed, run the website's `npm test`, then:
   ```sh
   node scripts/publish-highlights.cjs data/highlights.json --publish
   ```
   This publisher uses the existing Firebase CLI account; no separate login.
   It clones the **actual live version**, replaces only
   `/public/files/highlights.json`, verifies every other hash and exact config,
   refuses a concurrent production change before release, then verifies the public
   content. It updates the website source copy only after public verification.
   No whole-site build/deploy: the website checkout has unrelated unfinished work.
   No Functions deployment; NVIDIA model routing is untouched.
   `data/deployment.json` identifies the previous version for rollback, while
   `data/backups/<version>.json` contains its inventory/config/data.
8. If the website source file changed, verify there are no unrelated unpushed
   commits, then `git commit --only public/files/highlights.json` with a focused
   message and push the current tracking branch. Leave all other work untouched.
   Report publish/source-push failures independently; do not claim a scrape or
   release succeeded merely because the scheduler ran. Stay quiet on unchanged
   content; notify for new content, errors or required sign-in.

## Other paths and backups

- **Saved Playwright session:** `uv run kindle-highlights scrape --headless --auth
  session --fresh --out data/candidate.json`. Current tests still get Amazon's
  generic pre-login rejection even with the corrected `/notebook` URL, so do not
  use this as the weekly primary or repeatedly retry it. A manual visible session
  refresh may restore it. `--resume` only recovers interrupted new-book exports;
  it misses edits to existing books. Full candidate output must be checked before
  use; never publish after a nonzero scraper exit.
- **Kindle device `My Clippings.txt`:** retain a dated USB copy independently of
  Amazon. Readwise documents manual imports of this file, including personal
  documents missing from the cloud notebook. No device is connected/tested here,
  and no automatic local importer is installed by this change.
- **Readwise:** an optional paid/service dependency with browser-based Kindle sync,
  duplicate detection and downstream exports. Its Kindle connection still relies
  on the notebook, so it is not independent protection against an Amazon outage.
  No account, extension or subscription was created.
- Local content-addressed backups plus retained Firebase versions provide recovery
  for a bad publish. Keep an off-machine backup of `data/` through the user's
  existing backup system; local backups alone do not cover disk loss.

References: [Readwise Kindle import](https://docs.readwise.io/readwise/docs/importing-highlights/kindle),
[My Clippings import](https://docs.readwise.io/readwise/docs/importing-highlights),
[Codex scheduling](https://learn.chatgpt.com/docs/automations?surface=app).
