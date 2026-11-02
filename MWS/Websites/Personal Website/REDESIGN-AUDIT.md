# MWS audit and proposed architecture

Audit completed before implementation, November 2, 2026.

## Existing system
- Target: Python_Lab/MWS/Websites/Personal Website. Plain HTML/CSS/JavaScript; no dependency manifest, build, API, database, or upload endpoint.
- README specifies Python's static HTTP server and uploading the complete directory to the existing site root. Preserve relative URLs, assets, existing legacy demo URLs, privacy.html and terms.html.
- render.yaml configures Sacratissimum, a different project; do not alter it.
- Clean initial Git status; no repository AGENTS.md discovered.
- Contact email and telephone already present: maierwebsolutions@gmail.com and +1 225 678 7309. No verified payment processor. Do not add checkout or payment-method claims.
- Current navigation, fictional website previews, pricing calculator and policies promote website subscriptions; replace primary experience for the authorized repositioning, preserve legacy demo files.

## Security and reliability findings
- Current target has no server-side form processing, SQL, uploads, authentication or rate limiting surface. Host TLS, headers, logging and deployment configuration are unavailable; cannot verify their controls.
- Existing innerHTML assignments use fixed demonstration content; avoid interpolating visitor inputs into HTML in the replacement.
- Existing styles and demo pages load Google fonts/Unsplash resources. New primary pages will use local assets and system fonts; legacy demos retain their original behavior.
- No target dependency tree exists to run a package vulnerability audit against. Repository-wide history and unrelated applications require separate security review; no assurance of absence of historical secrets.
- Quote workflow needs a delivery provider/backend before true server submission. Preserve email transport, explicitly label preparation and handoff, provide manual copy fallback, store nothing in browser storage, disable uploads.
- Live lead delivery, payment processing, secure sample transfer, retention scheduling and production host configuration remain operational prerequisites; do not imply verified infrastructure.

## Architecture decision
Retain static hosting and dependency-free browser runtime. Home, Services, Examples, About, Contact, Terms and Privacy share one stylesheet and navigation. Central config owns five service scopes/prices and a manual foundingOffer.enabled flag. No remaining-spots counter or countdown. Fixed synthetic examples run locally: cleanup, inventory review, workflow simplification, filtered sales metrics and product matching.

Use semantic HTML, visible focus, labeled form controls, accessible tables, keyboard buttons, responsive grids, reduced-motion support and progressive enhancement. Shared script renders config-driven service cards using DOM APIs. Static content and direct email remain usable without JavaScript.

## Delivery checks
Serve the existing directory using Python; exercise pages with Playwright at desktop and mobile sizes. Check errors, internal links, configured prices, promotion disabled behavior, demo results, form validation and email handoff. No deployment or live customer contact during tests. Policies remain explicitly drafts for owner/legal review. Record reproducible startup and readiness instructions in the environment draft.

## Completed validation
Browser checks passed for seven primary pages at 1440px and 390px, internal links, mobile navigation/Escape, all five introductory and regular prices, disabled promotion state, five demonstrations, required form validation, safe text handling and email preparation. No browser JavaScript errors. Current target credential-pattern scan flagged zero files; this is not a full secret audit. Python static server and system Chromium were used; no dependency installation was required.

## Publication prerequisites
Owner must verify contact details, offer eligibility records and switch, finalize draft policies and adopt data retention procedures. Existing Client_Agreement_Template.txt is a legacy website agreement; do not use it for new data services. Prepare a reviewed data-services agreement separately. Live email delivery, secure transfer providers, host HTTPS/security headers and production redirects must be tested on the actual deployment. No site deployment or environment publication was performed.

A bounded common-credential-pattern scan also covered available Git history for this website path (`git log --all -p -- <target>`), completing successfully with zero matching pattern categories. This is not an exhaustive secret detector or a repository-wide security clearance. Final browser rerun passed after documentation and legacy-anchor updates.


## Readability and demonstration revision

Replaced the initial visual treatment with a navy hero, warm light backgrounds, mint accents, larger body text, stronger contrast, and distinct editorial sections. Copy uses the owner’s approved first-person voice. Services retain all prices and scopes, with optional examples/exclusions behind native disclosure controls.

The homepage now contains a functioning catalog cleanup preview. The examples page is a focused five-tab Data Lab with independent cleanup rules and CSV downloads, inventory review decisions, calculated automation outputs, linked sales filters/source rows, and matching/conflicting/incomplete product comparisons. Demonstrations remain isolated from customer data. Keyboard navigation supports arrow keys, Home, and End. No animation is required to understand results.

Removed 12 unused legacy stylesheet/script files and two unused full-logo duplicates. Retained old demo page addresses as minimal forwarding pages. No primary page references removed resources. No deployment configuration or unrelated application was changed.

The quote form now remains disabled until its JavaScript handler is installed. With JavaScript unavailable, a visitor uses direct email/phone instead of accidentally submitting form fields in a URL. No backend, upload, payment integration, or tracking was added.

Revision validation passed: 35 page/viewport combinations (seven primary pages at 320, 390, 768, 1024 and 1440 pixels); no horizontal page overflow or browser errors. Also verified introductory/regular price switching, visible base scopes, interactive homepage reset, independent cleanup rules, actual CSV contents, inventory review state, automation input/output totals, filtered report rows, all matching scenarios, keyboard tab controls, legacy forwarding pages, disabled no-JavaScript form with direct contact fallback, and the enlarged homepage layout. Static resource inspection found zero missing local HTML references. These are development checks, not a complete accessibility or security certification.
