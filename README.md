# Kindle Highlights Scraper

A Python 3.12 tool to scrape all Kindle highlights from Amazon's notebook page and export them to JSON.

Page: https://read.amazon.com/kp/notebook

## Features

- Scrapes all highlighted text from your Kindle library
- Authenticates with Amazon account (supports 2FA/TOTP)
- Persists login state to avoid repeated authentication
- Exports to structured JSON format
- Simple CLI interface
- Works with `uv` package manager

## Setup

### Prerequisites

- Python 3.12+
- `uv` package manager

### Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Install Playwright browser:
   ```bash
   uv run playwright install --with-deps chromium
   ```

4. Create environment file:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your Amazon credentials:
   ```
   AMAZON_EMAIL=your-email@example.com
   AMAZON_PASSWORD=your-password
   # Optional: for 2FA
   AMAZON_TOTP_SECRET=your-totp-secret
   ```

## Usage

### Basic scraping (all books):
```bash
uv run python -m kindle_highlights scrape --out data/highlights.json
```

### Scrape specific book by ASIN:
```bash
uv run python -m kindle_highlights scrape --asin B00X57B4JG --out highlights.json
```

### Run with visible browser (for debugging or manual 2FA):
```bash
uv run python -m kindle_highlights scrape --headful
```

## Output Format

The tool exports JSON in this structure:

```json
{
  "run": {
    "timestamp": "2025-09-13T12:34:56Z"
  },
  "books": [
    {
      "asin": "B00X57B4JG",
      "title": "Why Greatness Cannot Be Planned",
      "author": "Kenneth O. Stanley; Joel Lehman",
      "cover_url": "https://...",
      "highlights": [
        {
          "id": "highlight-...",
          "color": "yellow",
          "text": "...",
          "page": 8,
          "location": 283,
          "note": "optional"
        }
      ]
    }
  ]
}
```

## How It Works

1. **Authentication**: Uses Playwright to automate browser login to Amazon
2. **Session Persistence**: Saves authentication state to avoid repeated logins
3. **Book Discovery**: Scrolls through the library to find all annotated books
4. **Highlight Extraction**: For each book, scrolls through annotations to load all highlights
5. **Parsing**: Uses BeautifulSoup to extract structured data from HTML
6. **Export**: Saves everything to JSON with metadata

## Testing

Run the test suite:
```bash
uv run pytest tests/ -v
```

Test the parser offline:
```bash
uv run python test_parser.py
```

## Troubleshooting

- **2FA Issues**: Use `--headful` mode for manual 2FA entry
- **Login Problems**: Delete `playwright/.auth/user.json` to reset session
- **Missing Books**: Some books might have export limits - check for truncation warnings

## Architecture

- `kindle_highlights/parser.py`: HTML parsing logic with BeautifulSoup
- `kindle_highlights/scraper.py`: Playwright automation and scraping logic  
- `kindle_highlights/__main__.py`: CLI interface
- `tests/`: Pytest test suite using offline HTML sample

The implementation follows the plan in `PLAN.md` with TDD approach using `pageexample.html` for testing.

## Original Analysis

Amazon Kindle requests seem to be like this for a book by asin:

curl 'https://read.amazon.com/kp/notebook?asin=B003P9XC62&contentLimitState=&' \
  -H 'accept: */*' \
  -H 'accept-language: en-US,en;q=0.9' \
  -b 'session-id=131-2842127-6790611; ubid-main=130-8104810-5966362; lc-main=en_US; i18n-prefs=USD; at-main=Atza|IwEBIH53mbDINdQEHTRX-4x_-8kgFqqWn33Gk1K6Nb6N5KDFFb0wV9REmmEblflmePzGymuu7VrOtuUbCxKiAkMHVATXpVGJeaPX14Wzp5SQUMBU9ktOdKIaHHNwPljBoqEJQFko2CCsPMi9UWyvktR2xZAuYhjpouMA8NXm54d0ac1Vk3xXlg0al6T5GxmFWL5_WicXJcJN6qUhL_UrwWFZyGksYZaNvY9qF_dXRjsF9K6cqA; sess-at-main="r/eM1xb6fjFr/RfYOlSOBtzYcfGCJSV0ZYJJepxOunc="; sst-main=Sst1|PQF343K8Y-AOLgDoKB1ep-wHCY4NyuiC59egnEJtpE65fHLS4xDoIV1qmcRjv0gvD7NdaTWCRIev7CXGzZvk6F7bviEwA_V04eHkG0zzlspxdEn1c4O-nD6TzEKa_cbRuA4oAQKNC5_9WX0AUgRK5wIIHhw9B1O0GBOfpr9umTFtoSMybM9A5uM9sWEIk5tlgpRzHRJdH4Z8x4H5VEo-6MsjRP4lJkXXK_BRlvAdAhTtCTH58YdkNpIbgp6R58yDTvZGDwXr0C0_1T_PwgZe8kUEbY86EgmhphHwItQS1DZhHV8; session-id-time=2082787201l; session-token=lyYqtdN2oDaiEKko8s4Ppdu+B41nV8QAS2wGlTX905ZhkUA7jKG/M+9X4c4IwS/50WdKtJyWEWFHHBncnIkg+po4smDU6nRc4NqOqlyzMPCATlReWOdvTQcjtffVzt5fIZKqwdT2Yla1Cgh2Q/0jq4zlJrveI7Rv9UxMjSvFpSMdetS/itIRwx1XJdZzHgodbW3DR7M3EU+IgJe6GNEX8DDotfyfqNVhwna6qDhMoSBaJS1ZQCxuVj9vJl4ta6nQmB9fAlaF1SWZkRpFUrIp7qR3SEE+mifHSMCwcXLKz7uBUUxx5YhWwG3yWmHIzNxUFnlnkym50QmyVStQPTKSZW8tQBNC3Jz6mWYcCckPz47E2yTZusZLmsQP9FOEACrd; x-main="XOnVmfHQ?0EEX9vzr6ZUJeHpFBZRw1OfP0h8n5bY2r@NoISj133P4ZvxVcvqzIkg"; csm-hit=tb:8YSMZYV5ZBZ4N6BGX7PD+s-8YSMZYV5ZBZ4N6BGX7PD|1757735442372&t:1757735442372&adb:adblk_no' \
  -H 'dnt: 1' \
  -H 'priority: u=1, i' \
  -H 'referer: https://read.amazon.com/kp/notebook?ref_=k4w_ms_notebook' \
  -H 'sec-ch-ua: "Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'sec-gpc: 1' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36' \
  -H 'x-requested-with: XMLHttpRequest'

  Which then returns a response like this:

<!doctype html>
<html lang="en" class="a-no-js" data-19ax5a9jf="dingo">
    <body class="a-m-us a-aui_72554-c a-aui_a11y_6_837773-c a-aui_amzn_img_959719-c a-aui_amzn_img_gate_959718-c a-aui_killswitch_csa_logger_372963-t1 a-aui_pci_risk_banner_210084-c a-aui_template_weblab_cache_333406-c a-aui_tnr_v2_180836-c a-bw_aui_cxc_alert_measurement_1074111-c">
        <div id="a-page">
            <script type="a-state" data-a-state="{&quot;key&quot;:&quot;a-wlab-states&quot;}">
                {"AUI_KILLSWITCH_CSA_LOGGER_372963":"T1"}
            </script>
            <div id="annotation-section" class="a-section">
                <div id="annotation-scroller" class="a-scroller kp-notebook-scroller-addon a-scroller-vertical">
                    <!-- Add a nice message if a desktop user has been redirected -->
                    <div class="a-row a-spacing-top-extra-large kp-notebook-annotation-container">
                        <!-- This choice is for either a desktop- or mobile-oriented header -->
                        <!-- To handle tablet grid logic-->
                        <!-- To handle tablet grid logic-->
                        <div class="a-row a-spacing-base">
                            <div class="a-column a-span1 kp-notebook-bookcover-container">
                                <a class="a-link-normal kp-notebook-printable a-text-normal" target="_blank" rel="noopener" href="https://www.amazon.com/dp/B005DXR5ZC">
                                    <span class="a-declarative" data-action="kp-notebook-detail-page-url" data-kp-notebook-detail-page-url="{}">
                                        <img alt="" src="https://m.media-amazon.com/images/I/51ZFmRLeKLL._SY160.jpg" class="kp-notebook-cover-image-border"/>
                                    </span>
                                </a>
                            </div>
                            <div class="a-column a-span5">
                                <p class="a-spacing-small a-size-mini a-color-base kp-notebook-selectable kp-notebook-metadata a-text-bold a-text-caps">Your Kindle Notes For:</p>
                                <h3 class="a-spacing-top-small a-color-base kp-notebook-selectable kp-notebook-metadata">The Beginning of Infinity: Explanations That Transform the World</h3>
                                <p class="a-spacing-none a-spacing-top-micro a-size-base a-color-secondary kp-notebook-selectable kp-notebook-metadata">David Deutsch</p>
                                <span class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">
                                    Last accessed on &nbsp;<span id="kp-notebook-annotated-date"></span>
                                </span>
                            </div>
                        </div>
                        <div class="a-row a-spacing-large">
                            <div class="a-column a-span10 kp-notebook-row-separator">
                                <span class="a-size-base-plus a-color-base kp-notebook-selectable kp-notebook-metadata a-text-bold">
                                    <span id="kp-notebook-highlights-count">--</span>
                                    &nbsp;Highlight(s)<font color="gray">&nbsp;|&nbsp;</font>
                                    <span id="kp-notebook-notes-count">--</span>
                                    &nbsp;Note(s)
                                </span>
                                <div id="kp-notebook-hidden-annotations-summary" class="a-box a-alert-inline a-alert-inline-warning aok-hidden" aria-live="polite" aria-atomic="true">
                                    <div class="a-box-inner a-alert-container">
                                        <i class="a-icon a-icon-alert"></i>
                                        <div class="a-alert-content">Some highlights have been hidden or truncated due to export limits.</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <!-- Both mobile and desktop use the same JSP to render the actual annotations themselves -->
                        <div id="kp-notebook-annotations" class="a-row">
                            <input type="hidden" name="" value="eCbL5lL3ZPuu1qYvDglxw8infta%2Bwc1NZVrabCLigqvdasZaFifHlw%3D%3D" class="kp-notebook-content-limit-state"/>
                            <input type="hidden" name="" class="kp-notebook-annotations-next-page-start"/>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNDgxNjpISUdITElHSFQ6YTc0OWNkZTEwLTRiMTAtNDRmNC05MmM0LTU0OGE2ZjNhMjhjOA" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="99" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;2</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;2</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 2&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNDgxNjpISUdITElHSFQ6YTc0OWNkZTEwLTRiMTAtNDRmNC05MmM0LTU0OGE2ZjNhMjhjOA-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNDgxNjpISUdITElHSFQ6YTc0OWNkZTEwLTRiMTAtNDRmNC05MmM0LTU0OGE2ZjNhMjhjOA" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNDgxNjpISUdITElHSFQ6YTc0OWNkZTEwLTRiMTAtNDRmNC05MmM0LTU0OGE2ZjNhMjhjOA" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">Even a typical star converts millions of tonnes of mass into energy every second, with each gram releasing as much energy as an atom bomb. You will be told that within the range of our best telescopes, which can see more galaxies than there are stars in our galaxy, there are several supernova explosions per second, each briefly brighter than all the other stars in its galaxy put together.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTE0MDM6SElHSExJR0hUOmE3N2M5NTJjMi1iMjRmLTRlMDEtYjMxZC1kMjBkMTIxNzViOTc" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1010" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;56</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;56</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 56&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTE0MDM6SElHSExJR0hUOmE3N2M5NTJjMi1iMjRmLTRlMDEtYjMxZC1kMjBkMTIxNzViOTc-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTE0MDM6SElHSExJR0hUOmE3N2M5NTJjMi1iMjRmLTRlMDEtYjMxZC1kMjBkMTIxNzViOTc" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTE0MDM6SElHSExJR0hUOmE3N2M5NTJjMi1iMjRmLTRlMDEtYjMxZC1kMjBkMTIxNzViOTc" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">And so, again, everything that is not forbidden by laws of nature is achievable, given the right knowledge.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTI4MzM6SElHSExJR0hUOmE0NzY2ZjZhNi03YTg3LTQ5M2YtOGQyNC0yMzU3Y2I4MzQ1OGQ" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1019" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;56</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;56</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 56&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTI4MzM6SElHSExJR0hUOmE0NzY2ZjZhNi03YTg3LTQ5M2YtOGQyNC0yMzU3Y2I4MzQ1OGQ-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTI4MzM6SElHSExJR0hUOmE0NzY2ZjZhNi03YTg3LTQ5M2YtOGQyNC0yMzU3Y2I4MzQ1OGQ" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNTI4MzM6SElHSExJR0hUOmE0NzY2ZjZhNi03YTg3LTQ5M2YtOGQyNC0yMzU3Y2I4MzQ1OGQ" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">In theory a knowledgeable zoologist, presented with the complete transcript of a genome [the set of all the genes of an organism], should be able to reconstruct the environmental circumstances that did the carving. In this sense the DNA is a coded description of ancestral environments. In Art Wolfe, The Living Wild, ed. Michelle A. Gilders (2000)</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjU4Mjc6SElHSExJR0hUOmFjNTRhOWE1Zi01MGI2LTRiNWEtOTA1Zi03ZjFiNjQ4OWYzNWE" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1106" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;61</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;61</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 61&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjU4Mjc6SElHSExJR0hUOmFjNTRhOWE1Zi01MGI2LTRiNWEtOTA1Zi03ZjFiNjQ4OWYzNWE-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjU4Mjc6SElHSExJR0hUOmFjNTRhOWE1Zi01MGI2LTRiNWEtOTA1Zi03ZjFiNjQ4OWYzNWE" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjU4Mjc6SElHSExJR0hUOmFjNTRhOWE1Zi01MGI2LTRiNWEtOTA1Zi03ZjFiNjQ4OWYzNWE" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">Even today we have barely begun to examine that evidence: on any clear night, the chances are that your roof will be struck by evidence falling from the sky which, if you only knew what to look for and how, would win you a Nobel prize.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjYwNjM6SElHSExJR0hUOmE4N2UwMDAzZC0yMTQ2LTQ5MGMtYTI5NS0zZDFmMzEwOTVmYmE" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1108" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;61</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;61</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 61&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjYwNjM6SElHSExJR0hUOmE4N2UwMDAzZC0yMTQ2LTQ5MGMtYTI5NS0zZDFmMzEwOTVmYmE-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjYwNjM6SElHSExJR0hUOmE4N2UwMDAzZC0yMTQ2LTQ5MGMtYTI5NS0zZDFmMzEwOTVmYmE" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNjYwNjM6SElHSExJR0hUOmE4N2UwMDAzZC0yMTQ2LTQ5MGMtYTI5NS0zZDFmMzEwOTVmYmE" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">In chemistry, every stable element that exists anywhere is also present on or just below the Earth &rsquo;s surface.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNzI4ODI6SElHSExJR0hUOmFmMGZjNmUzZS0wMTQ2LTQ4OWQtODRjZi0wNDU1MTkyN2IyYTk" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1153" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;64</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;64</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 64&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNzI4ODI6SElHSExJR0hUOmFmMGZjNmUzZS0wMTQ2LTQ4OWQtODRjZi0wNDU1MTkyN2IyYTk-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNzI4ODI6SElHSExJR0hUOmFmMGZjNmUzZS0wMTQ2LTQ4OWQtODRjZi0wNDU1MTkyN2IyYTk" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoxNzI4ODI6SElHSExJR0hUOmFmMGZjNmUzZS0wMTQ2LTQ4OWQtODRjZi0wNDU1MTkyN2IyYTk" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">And so the maxim that I suggested should be carved in stone, namely &lsquo;The Earth &rsquo;s biosphere is incapable of supporting human life &rsquo;is actually a special case of a much more general truth, namely that, for people, problems are inevitable. So let us carve that in stone:</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyMDM0NzI6SElHSExJR0hUOmE2MTRkNjllMi00YTYwLTQ5OTktYmQ2OS0wMjQ2MGJiYzVmYzg" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1357" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;76</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;76</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 76&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyMDM0NzI6SElHSExJR0hUOmE2MTRkNjllMi00YTYwLTQ5OTktYmQ2OS0wMjQ2MGJiYzVmYzg-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyMDM0NzI6SElHSExJR0hUOmE2MTRkNjllMi00YTYwLTQ5OTktYmQ2OS0wMjQ2MGJiYzVmYzg" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyMDM0NzI6SElHSExJR0hUOmE2MTRkNjllMi00YTYwLTQ5OTktYmQ2OS0wMjQ2MGJiYzVmYzg" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">Both the Principle of Mediocrity and the Spaceship Earth idea are, contrary to their motivations, irreparably parochial and mistaken. From the least parochial perspectives available to us, people are the most significant entities in the cosmic scheme of things. They are not &lsquo;supported &rsquo;by their environments, but support themselves by creating knowledge. Once they have suitable knowledge (essentially, the knowledge of the Enlightenment), they are capable of sparking unlimited further progress.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNTMxMjU6SElHSExJR0hUOmE0YmFjNzkwNC1iZDQwLTQ4ZTQtOTI5NC1iNDI4NDY2YTA4NDQ" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1688" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;96</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;96</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 96&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNTMxMjU6SElHSExJR0hUOmE0YmFjNzkwNC1iZDQwLTQ4ZTQtOTI5NC1iNDI4NDY2YTA4NDQ-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNTMxMjU6SElHSExJR0hUOmE0YmFjNzkwNC1iZDQwLTQ4ZTQtOTI5NC1iNDI4NDY2YTA4NDQ" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNTMxMjU6SElHSExJR0hUOmE0YmFjNzkwNC1iZDQwLTQ4ZTQtOTI5NC1iNDI4NDY2YTA4NDQ" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">The physicist Brandon Carter calculated in 1974 that if the strength of the interaction between charged particles were a few per cent smaller, no planets would ever have formed and the only condensed objects in the universe would be stars; and if it were a few per cent greater, then no stars would ever explode, and so no elements other than hydrogen and helium would exist outside them. In either case there would be no complex chemistry and hence presumably no life.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNzg5NDQ6SElHSExJR0hUOmFhMDYyZTc5Mi0wNTZhLTQ1NmUtYjk5MS1jNTUwOWY0NjQ5OGU" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1860" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;107</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;107</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 107&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNzg5NDQ6SElHSExJR0hUOmFhMDYyZTc5Mi0wNTZhLTQ1NmUtYjk5MS1jNTUwOWY0NjQ5OGU-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNzg5NDQ6SElHSExJR0hUOmFhMDYyZTc5Mi0wNTZhLTQ1NmUtYjk5MS1jNTUwOWY0NjQ5OGU" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyNzg5NDQ6SElHSExJR0hUOmFhMDYyZTc5Mi0wNTZhLTQ1NmUtYjk5MS1jNTUwOWY0NjQ5OGU" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">This says that the only force on your arm in that situation is that which you yourself are exerting, upwards, to keep it constantly accelerating away from the straightest possible path in a curved region of spacetime.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyOTU5NzA6SElHSExJR0hUOmFiODJkODBiNS01YTgzLTRmNTYtOTg4ZC05NDgzMTU4NGI3YWE" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="1974" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;113</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;113</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 113&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyOTU5NzA6SElHSExJR0hUOmFiODJkODBiNS01YTgzLTRmNTYtOTg4ZC05NDgzMTU4NGI3YWE-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyOTU5NzA6SElHSExJR0hUOmFiODJkODBiNS01YTgzLTRmNTYtOTg4ZC05NDgzMTU4NGI3YWE" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzoyOTU5NzA6SElHSExJR0hUOmFiODJkODBiNS01YTgzLTRmNTYtOTg4ZC05NDgzMTU4NGI3YWE" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">Newton &rsquo;s predictions are indeed excellent in the context of bridge-building, and only slightly inadequate when running the Global Positioning System, but they are hopelessly wrong when explaining a pulsar or a quasar &ndash;or the universe as a whole. To get all those right, one needs Einstein &rsquo;s radically different explanations.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDQ3MTc6SElHSExJR0hUOmFhODdlNjc2YS01NTIwLTRlYjktOTlhZi00MTNjZjQyZDEzNjY" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="3365" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;196</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;196</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 196&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDQ3MTc6SElHSExJR0hUOmFhODdlNjc2YS01NTIwLTRlYjktOTlhZi00MTNjZjQyZDEzNjY-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDQ3MTc6SElHSExJR0hUOmFhODdlNjc2YS01NTIwLTRlYjktOTlhZi00MTNjZjQyZDEzNjY" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDQ3MTc6SElHSExJR0hUOmFhODdlNjc2YS01NTIwLTRlYjktOTlhZi00MTNjZjQyZDEzNjY" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">The possibilities that lie in the future are infinite. When I say &lsquo;It is our duty to remain optimists,&rsquo;this includes not only the openness of the future but also that which all of us contribute to it by everything we do: we are all responsible for what the future holds in store. Thus it is our duty, not to prophesy evil but, rather, to fight for a better world. Karl Popper, The Myth of the Framework (1994)</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDk2MzM6SElHSExJR0hUOmFmZmI2NmVlZC1kMzM2LTQyOGEtODhmYS1jNzNiYjQ4YTE5MmM" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="3398" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;198</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;198</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 198&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDk2MzM6SElHSExJR0hUOmFmZmI2NmVlZC1kMzM2LTQyOGEtODhmYS1jNzNiYjQ4YTE5MmM-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDk2MzM6SElHSExJR0hUOmFmZmI2NmVlZC1kMzM2LTQyOGEtODhmYS1jNzNiYjQ4YTE5MmM" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MDk2MzM6SElHSExJR0hUOmFmZmI2NmVlZC1kMzM2LTQyOGEtODhmYS1jNzNiYjQ4YTE5MmM" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">Following Popper, I shall use the term prediction for conclusions about future events that follow from good explanations, and prophecy for anything that purports to know what is not yet knowable.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MTMzNDU6SElHSExJR0hUOmExZTIyNGI4YS04MGMxLTQ2ZTktYTExZS0xZjVhZDNmYzNkMmU" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="3423" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;199</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;199</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 199&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MTMzNDU6SElHSExJR0hUOmExZTIyNGI4YS04MGMxLTQ2ZTktYTExZS0xZjVhZDNmYzNkMmU-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MTMzNDU6SElHSExJR0hUOmExZTIyNGI4YS04MGMxLTQ2ZTktYTExZS0xZjVhZDNmYzNkMmU" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1MTMzNDU6SElHSExJR0hUOmExZTIyNGI4YS04MGMxLTQ2ZTktYTExZS0xZjVhZDNmYzNkMmU" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">When the determinants of future events are unknowable, how should one prepare for them? How can one? Given that some of those determinants are beyond the reach of scientific prediction, what is the right philosophy of the unknown future? What is the rational approach to the unknowable &ndash;to the inconceivable? That is the subject of this chapter.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NDQ0OTU6SElHSExJR0hUOmFmODQ2MzU1Yi1kMmZiLTRmMTktYWIyNy0xMmUyMzc1MjBhMjU" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="3630" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;211</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;211</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 211&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NDQ0OTU6SElHSExJR0hUOmFmODQ2MzU1Yi1kMmZiLTRmMTktYWIyNy0xMmUyMzc1MjBhMjU-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NDQ0OTU6SElHSExJR0hUOmFmODQ2MzU1Yi1kMmZiLTRmMTktYWIyNy0xMmUyMzc1MjBhMjU" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NDQ0OTU6SElHSExJR0hUOmFmODQ2MzU1Yi1kMmZiLTRmMTktYWIyNy0xMmUyMzc1MjBhMjU" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">Advocates of violence usually have in mind that none of those things need happen if only everyone agreed on who should rule. But that means agreeing about what is right, and, given agreement on that, rulers would then have nothing to do. And, in any case, such agreement is neither possible nor desirable: people are different, and have unique ideas; problems are inevitable, and progress consists of solving them.</span>
                                                <div></div>
                                            </div>
                                            <!-- Placeholder for if a child note is added by the customer -->
                                            <div id="note-" class="a-row a-spacing-top-base kp-notebook-note aok-hidden kp-notebook-selectable">
                                                <span id="note-label" class="a-size-small a-color-secondary">
                                                    Note:<span class="a-letter-space"></span>
                                                </span>
                                                <span id="note" class="a-size-base-plus a-color-base"></span>
                                            </div>
                                            <!-- Orphaned note without associated highlight -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div id="QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NTg1OTA6SElHSExJR0hUOmEzMzMyNzE4Ny0wZGQ0LTRhNTEtYTgyZS05YzUwMWI0YzEwOTI" class="a-row a-spacing-base">
                                <div class="a-column a-span10 kp-notebook-row-separator">
                                    <!-- Header row containing: optionally a star, note/highlight label, page/location information, and an
            options dropdown -->
                                    <div class="a-row">
                                        <input type="hidden" name="" value="3724" id="kp-annotation-location"/>
                                        <!-- optional star, note/highlight label, page/location -->
                                        <div class="a-column a-span8">
                                            <!-- Star, if necessary -->
                                            <!-- Highlight -->
                                            <!-- Highlight header -->
                                            <span id="annotationHighlightHeader" class="a-size-small a-color-secondary kp-notebook-selectable kp-notebook-metadata">Yellow highlight | Page:&nbsp;216</span>
                                            <!-- Note header in case highlight is deleted, and we need to have the note header -->
                                            <span id="annotationNoteHeader" class="a-size-small a-color-secondary aok-hidden kp-notebook-selectable kp-notebook-metadata">Note | Page:&nbsp;216</span>
                                            <!-- Freestanding note header -->
                                        </div>
                                        <!-- the Options menu -->
                                        <div class="a-column a-span4 a-text-right a-span-last">
                                            <span class="a-declarative" data-action="a-popover" data-a-popover="{&quot;closeButton&quot;:&quot;false&quot;,&quot;closeButtonLabel&quot;:&quot;Close&quot;,&quot;activate&quot;:&quot;onclick&quot;,&quot;width&quot;:&quot;200&quot;,&quot;name&quot;:&quot;optionsPopover&quot;,&quot;position&quot;:&quot;triggerVerticalAlignLeft&quot;,&quot;popoverLabel&quot;:&quot;Options for annotations at Page 216&quot;}" id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NTg1OTA6SElHSExJR0hUOmEzMzMyNzE4Ny0wZGQ0LTRhNTEtYTgyZS05YzUwMWI0YzEwOTI-action">
                                                <a id="popover-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NTg1OTA6SElHSExJR0hUOmEzMzMyNzE4Ny0wZGQ0LTRhNTEtYTgyZS05YzUwMWI0YzEwOTI" href="javascript:void(0)" role="button" class="a-popover-trigger a-declarative">
                                                    Options<i class="a-icon a-icon-popover"></i>
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    <!-- Container for text content of the note / highlight -->
                                    <div class="a-row a-spacing-top-medium">
                                        <div class="a-column a-span10 a-spacing-small kp-notebook-print-override">
                                            <!-- Highlight with a child note -->
                                            <!-- Highlight without a child note -->
                                            <!-- Highlight text -->
                                            <div id="highlight-QTJaQk1UUzM1S0FVRjc6QjAwNURYUjVaQzo1NTg1OTA6SElHSExJR0hUOmEzMzMyNzE4Ny0wZGQ0LTRhNTEtYTgyZS05YzUwMWI0YzEwOTI" class="a-row kp-notebook-highlight kp-notebook-selectable kp-notebook-highlight-yellow">
                                                <span id="highlight" class="a-size-base-plus a-color-base">The best-known mini-enlightenment was the intellectual and political tradition of criticism in ancient Greece which culminated in the so-called &lsquo;Golden Age &rsquo;of the city-state of Athens in the fifth century BCE. Athens was one of the first democracies, and was home to an astonishing number of people who are regarded to this day as major figures in the history of ideas, such as the philosophers Socrates, Plato and Aristotle, the playwrights Aeschylus, Aristophanes, Euripides and Sophocles, and the historians Herodotus, Thucydides and Xenophon. The Athenian philosophical tradition continued a tradition of criticism dating back to Thales of Miletus over a century earlier and which had included Xenophanes of Colophon (570 &ndash;480 BCE), one of the first to question anthropocentric theories of the gods. Athens grew wealthy through trade, attracted creative people from all over the known world, became one of the foremost military powers of the age, and built a structure, the Parthenon, which is to this day regarded as one of the great architectural achievements of all time. At the height of the Golden Age, the Athenian leader Pericles tried to explain what made Athens successful. Though he no doubt believed that the city &rsquo;s patron goddess, Athena, was on their side, he evidently did not consider &lsquo;the goddess did it &rsquo;to be a sufficient explanation for the Athenians &rsquo;success. Instead, he listed specific attributes of Athenian civilization. We do not know exactly how much of what he described was flattery or wishful thinking, but, in assessing the optimism of a civilization, what that civilization aspired to be must be even more important than what it had yet succeeded in becoming. The first attribute that Pericles cited was Athens &rsquo;democracy. And he explained why. Not because &lsquo;the people should rule &rsquo;, but because it promotes &lsquo;wise action &rsquo;. It involves continual discussion, which is a necessary condition for discovering the right answer, which is in turn a necessary condition for progress:</span>
                                                <div></div>
            ...
</html>
