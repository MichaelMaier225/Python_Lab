# Maier Web Solutions

Static small-business data services website. No build step, package installation, API keys, backend, database, or payment integration is needed.

## Local development

Use the existing checkout; cloud tasks are already isolated. From `MWS/Websites/Personal Website`:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Request `/index.html` locally and verify it contains “Less busywork.”. Python 3.12 was tested. This server is for local development, not production.

## Structure

- `index.html`, `services.html`, `examples.html`, `about.html`, `contact.html`: primary pages.
- `site-config.js`: all five prices, base scopes, exclusions, and `foundingOffer.enabled`. Set this flag to `false` to close promotional pricing across primary pages. Track qualification in real business records; no automated spot count exists.
- `mws.js`, `mws.css`: shared behavior and responsive visual design.
- `terms.html`, `privacy.html`: drafts requiring owner/legal review before publication.
- `REDESIGN-AUDIT.md`: inspection, architecture, validation and limitations.
- `demo-*.html`, legacy CSS/scripts and assets: retained for old URLs; no longer loaded by primary pages.
- `Client_Agreement_Template.txt`: legacy website-services draft, not suitable for the new data-services work.

## Contact and data

The form validates and prepares an email, with a manual copy fallback. It does not send, upload, store, or collect payments. A visitor must send the prepared email. Email/telephone are preserved from the original website and need owner confirmation. Agree on secure sample transfer after initial contact.

Services and demos require JavaScript for their dynamic detail. Direct contact and core static page copy remain available without JavaScript.

## Deployment

Upload the entire website directory to the existing static site root, including new pages, config, scripts, stylesheet and existing assets. Preserve relative paths and existing legacy demo URLs. Do not change root `render.yaml`: it belongs to Sacratissimum. Existing signed website agreements are not amended by this redesign.

Before publication, verify host HTTPS and security headers, review policies, confirm promotion status and contact details, and test deployed navigation and actual email handoff. There is no verified payment processor or secure upload service.

## Validation

Playwright with installed system Chromium exercised seven pages at desktop/mobile widths, internal links, pricing and promotion disabled behavior, all five examples, mobile menu, form validation and safe email preparation. No browser errors or horizontal page overflow at 1440px/390px. No live emails, customer data, or payments were used. The external audit report and screenshots are in `/workspace/mws-review` in the current instance.
