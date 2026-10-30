# Sacratissimum

A Django Christian apparel **showcase**: high-contrast editorial homepage, searchable/filterable collection, product details and brand story. The visual identity includes cross motifs and explicitly Christ-centered copy, welcoming Christians across denominations. The disposable preview remains a showcase. A staged inventory/accounts/Stripe **test** checkout foundation is documented in [COMMERCE.md](COMMERCE.md); it is disabled on the public preview. There is no newsletter. The storefront makes no shipping, manufacturing or donation claims.

## Local setup

Run from `MWS/Websites/Sacratissimum` with Python 3.12 or newer supported by Django 5.2:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On Windows, activate with `.venv\Scripts\activate` instead. Local development uses an ignored `local.sqlite3` database. The old `db.sqlite3` and compiled files are no longer tracked; a local copy is retained on this working machine. Back up any old database changes before merging a removal into another checkout. Migrations initialize the product tables. Back up any database containing valuable data before migrating. To use a separate database, set `SACRATISSIMUM_DB_PATH` to an absolute SQLite path before running management commands.

Open the local server in your development browser. `/admin/` is the owner's management interface. Customer account behavior and production prerequisites are covered in [COMMERCE.md](COMMERCE.md). Production admin requires an enrolled authenticator; local development admin stays usable while setting up.

## Optional demo content

```bash
# Creates three fictional concepts as UNPUBLISHED drafts:
python manage.py load_demo_products
```

To display those drafts, select **Is published** on each product in admin. Alternatively, on a fresh database, explicitly opt into publishing newly created demo concepts:

```bash
python manage.py load_demo_products --publish
```

All demo products carry visible “Demo concept” labels and illustrative prices. They are not real merchandise or offered for sale. The command is repeatable and **never overwrites existing products**, including existing drafts: rerunning with `--publish` does not publish drafts created on a previous run. Use admin for subsequent edits and publication. Empty collections have a designed empty state.

## Managing real products

1. Create a product in admin: name, unique slug, description, USD price, availability.
2. Upload owned/licensed JPG, PNG or WebP product photos in the image inline. Add meaningful alt text. Lowest display order is the cover; additional photos form a gallery. Photos are uploaded to `media/` and not committed to Git.
3. Add each genuine size/color combination in the variant inline. Inactive variants stay hidden. Variants now track physical and reserved stock. Open a variant in admin and use **Adjust stock** to record changes with an audit reason. Availability remains an owner-managed product label; checkout rechecks physical availability atomically. Internal Code 128 labels are downloadable from the variant admin.
4. Select **Is featured** to include it on the homepage (first three by display order), and **Is published** when it is ready. Leave **Is demo** checked for fictional concepts; only uncheck it for actual products.

Prices use decimal fields and are labeled USD. Variant IDs identify internal barcode labels; optional SKUs remain owner-managed. The commerce app adds orders and stock audit records without collecting card data.

## Assets and content still needed

- Real product photography (cover plus alternate angles), preferably consistent 4:5 framing.
- Confirmed product names, designs, USD prices, fabrics, fit, sizing and care information, colors and availability.
- Approved brand logo if desired; the current wordmark is live text.
- Real public contact details and approved social links. None have been invented.
- Business and purchase policies when actual sales are introduced. There is no checkout in this version.

The hero charcoal campaign image (`campaign-charcoal.webp`; original PNG retained) is AI-generated concept art, explicitly labeled as a concept rather than real merchandise. It is not a product photograph or a manufacturing claim. The three distinct demo designs are original SVG concept illustrations, organized under `clothing/faith-edit/`. Non-demo products continue to use a neutral placeholder until real photography is uploaded. No external stock photos, fonts, trackers or CDNs are loaded. Typography uses locally available Georgia and Arial system fonts. Body text, navigation, controls and product details use readable, high-contrast type. The homepage uses a full-viewport campaign with centered branding and a shared desktop/mobile drawer; the catalog retains its responsive grid. Repeated copy is kept concise. The campaign WebP is about 315 KB instead of the original 2.77 MB PNG.

Interactive features include a shared accessible side menu; a native swipeable featured-product rail with keyboard/buttons and position feedback; collapsible mobile catalog filters; server-backed collection search, active-variant color filtering and price/name sorting, with debounced JavaScript updates; gallery thumbnails; a keyboard-accessible full-size image dialog; story question accordions; and a back-to-top control that returns keyboard focus to the header. Search/filter forms and gallery links still work without JavaScript. Motion respects reduced-motion preferences.

## Validation

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The tests cover published/draft behavior, empty states, decimal price validation, safe description rendering, active size/color combinations, unique variants, image galleries, admin access and editing forms, bounded catalog queries, search/color/sort behavior, distinct demo art, and safe repeatable demo creation.

Chromium checks covered all four page types at 320, 360, 390, 430, 768, 900, 1024 and 1440 CSS pixels, no horizontal overflow or broken displayed images, mobile menu keyboard behavior, reduced motion, concept switching, live search/color/sorting, rapid search updates, empty results and empty catalogs, image dialog Escape/focus return, story accordions, back-to-top focus, and filtering without JavaScript. The mobile polish also passed native touch-swipe emulation, rail keyboard/end-state checks, collapsible filters, product reading order and automated Axe WCAG A/AA scans on all four pages at mobile and desktop sizes. These are automated Chromium checks, not a certification of accessibility. Other browser engines and physical devices were not tested.

For internal cloud validation, the prepared interpreter is `/workspace/.venvs/sacratissimum/bin/python`. Use that path in place of `python` if not activating your own venv.

## Free Render preview (prepared, not deployed)

See [RENDER.md](RENDER.md) for the exact free service settings, build/start commands, environment variables, and validation commands. The repository-root `render.yaml` is an optional Blueprint for a single free web service; it creates no database, cache, persistent disk, or paid resource. It must be reviewed and deployed by you.

The preview uses Gunicorn, WhiteNoise, `DEBUG=False`, an environment-only secret and Render's exact assigned hostname. Static demo artwork is committed and collected at build time. On every process start, migrations run before the idempotent demo loader and Gunicorn. Preview SQLite lives in `/tmp`; data and uploaded files are disposable. No admin account is created. Local development and optional local demo loading remain unchanged.

This configuration is for sharing a disposable showcase, not a live shop. Real product uploads need durable storage and a production media-serving strategy before real business use. No deployment or paid services are part of this change.

## Structure

- `store/models.py`, `admin.py`: products, uploaded images and variants.
- `store/templates/store/`: shared layout, header/footer/cards and four page templates.
- `store/static/store/`: CSS, progressive menu/gallery JavaScript and original SVG art.
- `store/management/commands/load_demo_products.py`: opt-in fictional content.
- `store/migrations/`: versioned database schema; `store/tests.py`: behavior tests.

## Store foundation

See [COMMERCE.md](COMMERCE.md) for inventory/barcodes, verified accounts, administrator MFA, permanent database/media/email setup, Stripe sandbox setup, stock/payment recovery, Git protection and the remaining live-store requirements. US shipping is selected; its fee is not decided. No live checkout or external services have been enabled.

## Code layout and development checks

- `commerce/accounts.py`: registration, verification and staff authenticator enrollment.
- `commerce/views.py`: HTTP handlers for bags, checkout and owned orders.
- `commerce/inventory.py`: stock changes and reservations.
- `commerce/payments.py`: Stripe integration and verified payment transitions.
- `commerce/security.py`: shared preview access, throttles and verification tokens.
- `commerce/notifications.py`: transactional email.
- `commerce/admin_site.py`: the configured Django admin authentication policy.

Install `requirements-dev.txt` for consistent formatting and linting:

```bash
python -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
python manage.py test
```

Account templates are formatted with `djhtml --tabwidth 2 commerce/templates`.
The cleanup preserves existing URLs and database migrations.
