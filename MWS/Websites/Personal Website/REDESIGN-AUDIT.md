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


## Contrast, movement, and FAQ revision

Replaced the muted mint treatment with charcoal/cobalt/yellow contrast, original inline hero artwork, illustrated service headers, a dark featured service, a cobalt examples section, and dark FAQ controls. Short one-time entrance effects and pointer hover feedback respect reduced motion; content has no animation dependency. No runtime packages or external assets were added.

Converted the five FAQ headings to actual button controls with explicit expanded state and labeled answer regions. Control-only caret/selection styling avoids a text-insertion appearance while preserving visible keyboard focus and normal form carets. A browser-wide caret-browsing preference cannot be diagnosed from a screenshot; F7 can toggle it in browsers that support it.

The provided Lounge Lizard URLs could not be inspected: the configured HTTP proxy returned CONNECT 403. Their two hostnames were added to the environment configuration draft, preserving existing custom domains and presets; draft persistence does not apply runtime networking. The implementation follows the requested stronger visual character without claiming a direct comparison against those inaccessible pages.

Validation: the existing 35 page/viewport and functional checks passed. Additional checks passed for FAQ click/Enter/Space, independent open states, focus retention, control-only transparent caret, visible contact-input caret, correct hero nesting, mobile FAQ, and disabled animation under reduced motion. Browser-wide F7 behavior is not simulated by these tests.

## Work-centered redesign

Rebuilt the homepage around a specific recurring-spreadsheet problem, a side-by-side synthetic export, and three customer-problem paths leading to the five existing services. The product example now calculates a normalized export, highlights changed cells, preserves a missing price for review, exposes per-SKU decision notes, and produces both a CSV and text review notes. The related demonstration case study explains the format/deduplication/missing-value decisions without claiming customer results. The Data Lab retains its original customer source alongside the configurable result. First-person copy is shorter and more concrete.

Replaced the prior circles, tilted preview, generic service-card grid, watermark and decorative entrance effects with one source→decisions→output visual system. Rebuilt the shared stylesheet rather than stacking another theme. All pricing and base scopes remain centralized and unchanged. Removed the obsolete homepage preview renderer and old mini-demo implementation.

Contact now starts with direct email and offers the guided email-preparation tool as an optional disclosure. No unconfigured backend or delivery provider was invented. Policy labels are normal public labels; legal review is still pending and explicitly flagged in PUBLICATION.md. No portrait, clients, credentials, certifications, or outcomes were invented.

A reusable browser regression runner is included at checks/browser.cjs. It exercises 35 page/viewport combinations, existing services/offer logic, five Data Lab demos, source preservation, side-by-side catalog transformations, per-SKU inspection, both catalog downloads, no-JavaScript fallbacks, FAQ keyboard controls, contact preselection and safe email preparation. Screenshots and downloaded artifacts go outside the checkout.

Final validation passed for the work-centered revision: all 35 page/viewport combinations, existing functional regressions, source preservation, exact output and review-note file contents, three problem paths and five service prices, keyboard FAQ operation, reduced-motion behavior, optional guided contact preselection, safe email preparation, and no-JavaScript alternatives. No browser errors or missing local HTML resources. Desktop and mobile screenshots were visually inspected. Server submission and legal review remain unimplemented/unverified prerequisites documented in PUBLICATION.md.


## Preferred dark direction, new typography and actual owner logo

Restored the user-preferred dark split hero, white headline, yellow italic accent and blue artwork. Applied the same visual language across Services, the Data Lab, About, Contact and policy pages while keeping light surfaces where tables and form fields need them. Replaced system/Georgia typography with locally hosted Manrope variable and Instrument Serif Italic, including OFL license files and Latin subsets totaling about 67.5 KB.

The header/footer use an unchanged copy of the actual logo at MWS/MWS Logo/Maier Web Solutions Logo.png. A SHA-256 comparison confirmed equality to the source. The old promotional banner was not used because it describes the prior business offering. The compact hero preview and full comparison share the same transformation state; either reset restores both views. All source/output inspection and downloads remain available.

Validation passed for all 35 page/viewport combinations, local font loading, logo references, synchronized preview/run/reset, existing five demos, prices/offer, FAQ, downloads and email preparation. All visible paragraphs were additionally checked for at least 4.5:1 contrast against their solid ancestor backgrounds at desktop/mobile sizes; no failures were reported. This bounded check is not a full accessibility audit. Font checks explicitly load the italic face on policy pages where it is otherwise unused. Mobile contrast issues identified during review were corrected before the passing run.


## Unified opening refinement

Confirmed the second supplied screenshot as the layout target. Kept the dark split headline/compact example and removed the repeated full comparison from the normal page flow. The larger source/output view and downloads are an optional native disclosure within that same opening; existing #work links reveal it. Preview counts now explicitly describe the selected subset (three of five source rows, two of four output rows), with the complete dataset and export unchanged. The header displays the owner’s complete logo once, removing the redundant adjacent wordmark. No new dependency or external request was added.


## Balanced section contrast

Preserved the approved dark split hero, compact synchronized preview, owner logo and fonts. Replaced the mostly dark page background with warm white and introduced a deliberate light/dark sequence: warm-white service entry points, pale-blue example explanation, dark owner section, light FAQ, cobalt final CTA and pale footer. Inner pages now use brighter reading surfaces while retaining dark service overviews and light scope/tool panels. Removed dark-only foreground colors from affected sections rather than adding an independent theme layer.

All 35 layout/functional checks passed after the changes. A desktop/mobile contrast sweep across all seven primary pages also passed; that bounded check covers visible paragraphs, headings, links and buttons against solid ancestor backgrounds. The same regression check is now part of checks/browser.cjs, including italic accent text. No application behavior, pricing or external services changed.
