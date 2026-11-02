# Maier Web Solutions

Static small-business data services website. No build step, package installation, API keys, backend, database, or payment integration is needed.

## Local development

Use the existing checkout; cloud tasks are already isolated. From `MWS/Websites/Personal Website`:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Request `/index.html` locally and verify it contains “Your business.”. Python 3.12 was tested. This server is for local development, not production.

## Structure

- `index.html`, `services.html`, `examples.html`, `about.html`, `contact.html`: primary pages.
- `site-config.js`: all five prices, base scopes, exclusions, and `foundingOffer.enabled`. Set this flag to `false` to close promotional pricing across primary pages. Track qualification in real business records; no automated spot count exists.
- `mws.js`, `mws.css`: navigation, centralized pricing, quote preparation, and the responsive design system.
- `demos.js`: isolated synthetic-data demonstrations, tab navigation, transformations, and CSV downloads.
- `terms.html`, `privacy.html`: drafts requiring owner/legal review before publication.
- `REDESIGN-AUDIT.md`: inspection, architecture, validation and limitations.
- `demo-*.html`: small forwarding pages preserving old links to the current Data Lab. Legacy theme, calculator, slideshow and portfolio code, plus two unused logo duplicates, have been removed.
- `Client_Agreement_Template.txt`: legacy website-services draft, not suitable for the new data-services work.

## Contact and data

The form validates and prepares an email, with a manual copy fallback. It does not send, upload, store, or collect payments. A visitor must send the prepared email. Email/telephone are preserved from the original website and need owner confirmation. Agree on secure sample transfer after initial contact.

Services and demos require JavaScript for their dynamic detail. Direct contact and core static page copy remain available without JavaScript.

## Deployment

Upload the entire website directory to the existing static site root, including new pages, config, scripts, stylesheet and existing assets. Preserve relative paths and existing legacy demo URLs. Do not change root `render.yaml`: it belongs to Sacratissimum. Existing signed website agreements are not amended by this redesign.

Before publication, verify host HTTPS and security headers, review policies, confirm promotion status and contact details, and test deployed navigation and actual email handoff. There is no verified payment processor or secure upload service.

## The Data Lab

The homepage includes a side-by-side product catalog cleanup with inspectable decisions and downloadable CSV/review notes. Three problem-based paths lead to all five services. The Data Lab provides five keyboard-accessible examples:

- Customer cleanup: independent formatting and duplicate rules, flagged missing values, reset, and CSV export.
- Inventory review: normalized SKU grouping, price conflicts, missing prices, and explicit review decisions.
- Automation: transform two differently named input formats into calculated product totals, with source records and downloadable summary.
- Reporting: filter two months and two categories; totals, top product, chart, and source rows update together.
- Matching: compare matching attributes, conflicting sizes, and incomplete records. Candidates require human review.

These examples use only fixed synthetic records and do not accept customer files. Data and rules are in `demos.js`. They run locally without services or tracking.

## Validation

Playwright with installed system Chromium exercises seven pages at 320, 390, 768, 1024, and 1440 pixels. Checks cover internal links, pricing and promotion closing, service scope visibility, all interactive state changes, alternate cleanup rules, CSV contents, calculated totals, review decisions, matching counterexamples, keyboard tab navigation, safe email preparation, legacy forwarding pages, and no-JavaScript navigation. No live emails, customer data, or payments are used. The validation script and screenshots are in `/workspace/mws-review` in this instance.

If JavaScript is unavailable, contact fields remain disabled to prevent accidental query-string submission; direct email/phone alternatives and navigation remain available.

## Visual interaction and FAQ behavior

The site uses the preferred dark split hero and a consistent navy, cobalt, and yellow treatment across pages, with light surfaces for tables and forms. A compact hero preview stays synchronized with the larger source → decisions → output comparison. Original inline artwork and service icons need no external assets. No video, stock-image requests, animation library, or tracking is added.

FAQ headings are actual buttons controlling labeled answer regions through `aria-expanded` and `aria-controls`. Mouse, Enter, and Space toggle each answer independently. Only the control text suppresses selection and caret display; form fields retain their typing caret. All FAQ answers are readable without JavaScript. A caret visible elsewhere on ordinary page text may be the browser’s F7 caret-browsing mode.

Motion is limited to changed-cell feedback, report bars, and FAQ state changes. General entrance animations and decorative transforms have been removed. The interactions work without motion, and reduced-motion preferences are respected.

## Reusable browser checks

`checks/browser.cjs` runs the site’s meaningful regression checks. Use Node.js and an available Playwright installation with Chromium; neither is a runtime dependency of the site. With the local server running, this cloud environment can run:

```sh
MWS_PLAYWRIGHT_MODULE=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright \
MWS_BROWSER=/usr/bin/chromium \
node checks/browser.cjs
```

On a machine where Playwright is available through Node’s normal module resolution, omit `MWS_PLAYWRIGHT_MODULE`. Set `MWS_BROWSER` to that machine’s Chromium executable, `MWS_BASE_URL` to another local test server, or `MWS_ARTIFACT_DIR` to select an output directory. By default, screenshots and downloaded sample files are written outside the checkout under a fresh temporary directory.

The contact page offers direct email first. Its optional guided form still prepares an email for the visitor to send; no submission provider has been configured. Do not claim server-side delivery.

## Fonts and owner branding

The main face is **Manrope**, with **Instrument Serif Italic** for accent headings. Latin WOFF subsets are served locally from `assets/fonts/` with `font-display: swap`, so no Google Fonts requests are made at runtime. Font files total approximately 67.5 KB. OFL licenses and source details are included in that directory.

The header/footer image is an unchanged copy of `MWS/MWS Logo/Maier Web Solutions Logo.png`, deployed as `assets/mws-owner-logo.png`. The separate promotional banner describes the former website offering and is not used. Include all new font, license, and logo files when publishing the static directory.
