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

The homepage includes a working catalog cleanup preview. The Data Lab provides five keyboard-accessible examples:

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

The site uses charcoal, cobalt, warm white, and yellow for stronger section contrast. The hero artwork is an original inline SVG; service icons are inline SVG as well. No video, stock-image requests, animation library, or tracking is added.

FAQ headings are actual buttons controlling labeled answer regions through `aria-expanded` and `aria-controls`. Mouse, Enter, and Space toggle each answer independently. Only the control text suppresses selection and caret display; form fields retain their typing caret. All FAQ answers are readable without JavaScript. A caret visible elsewhere on ordinary page text may be the browser’s F7 caret-browsing mode.

Entrance effects run once as content comes into view, and card/button hover effects are limited to devices with hover support. Content is visible without motion. Reduced-motion preferences disable entrances and decorative transforms; changing that preference while viewing stops active page animations.
