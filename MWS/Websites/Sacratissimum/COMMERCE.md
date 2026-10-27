# Accounts, inventory and Stripe test checkout

This branch adds the store foundation without turning the disposable preview into a live shop. **No services were provisioned, no real Stripe requests were made, no money was charged, and no public/default admin account was created.** Do not supply live Stripe keys: this implementation explicitly rejects them.

## What is implemented

- Physical and reserved units for every product size/color variant, with a database constraint preventing stock below reservations.
- Staff stock adjustments with reasons, actor/time and an immutable inventory journal; paid orders deduct stock once.
- Optional owner SKUs and unique internal Code 128 identifiers (`SAC` + variant database ID). Staff can download SVG barcode labels and scan/search the identifier in the variant admin. These are internal labels, **not licensed GS1/UPC/EAN numbers**. Preserve the database IDs in backups/migrations.
- Customer registration, hashed passwords using Django's password hasher, 12-character minimum, email activation, login/logout, password reset/change and private order history. Activation requires an explicit confirmation POST; a mail scanner visiting the link does not activate an account. Tokens expire after one hour. Password changes invalidate other sessions.
- Axes login protections plus a persistent account-level attempt ceiling, including wrong administrator OTP attempts. Five attempts lock sign-in for fifteen minutes; successful login resets the application counter. No arbitrary forwarded IP header is trusted. Registration, email/resend and checkout have additional limits.
- Mandatory authenticator codes for production Django admin, enrolled only after authenticating and reconfirming the administrator password. Enrollment seeds are not exposed to anonymous requests or stored in Git. Existing devices cannot be replaced through a password-only public flow. Customer MFA is not advertised; this enrollment is specifically for staff.
- Session bag with server-side prices, quantity limits, CSRF-protected changes and a single active checkout per customer. An active checkout must be canceled/completed before changing the bag.
- Stripe-hosted **test-mode**, card-only checkout. The app never receives full card numbers, security codes or raw card input. It records payment references, order totals, shipment details and status. No customer billing portal, subscriptions or saved card vault is implemented.
- Stripe automatic tax, shipping-address collection, signed/age-checked webhooks, duplicate-event handling, payment/price/currency/tax/address checks, late-payment review, refund status and manual shipment tracking in admin. Browser success URLs never mark an order paid.
- Optional PostgreSQL (`DATABASE_URL`) and S3-compatible product-media configuration; SMTP delivery; private error reporting and access logs that omit token-bearing paths.

## What remains deliberately disabled

The free Render preview continues to load labeled demo products into temporary SQLite. It does **not** accept customer signups, bags or payments. Demo concepts are never purchasable, even if stock is set manually.

USD and **US shipping** are the initial scope. The shipping fee is undecided: `SHIPPING_RATE_CENTS` defaults to `-1`, so checkout remains closed. No free shipping, delivery date, return policy or tax-registration claim has been invented.

Real products/photos, final sizing/care details, public contact information, approved business/return/shipping/privacy policies, durable services and a live-mode review are still needed before real selling. Account/address deletion and retention procedures must be decided for your business; this is not a legal-policy generator.

## Local development

From `MWS/Websites/Sacratissimum`:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Use your existing virtual environment. On Windows, replace `python` with `.\.venv\Scripts\python.exe` if it is not activated. Existing products migrate with **zero physical and reserved stock**; no inventory count is invented. The normal local database is ignored `local.sqlite3`.

Local registration uses console email by default. A developer can follow its private verification/reset link; do not share those logs. Production never uses console email for account tokens. Set `SITE_URL` if running a development server on a different host/port.

To manage inventory, create a real (non-demo) product, add size/color variants, then open a variant in admin and use **Adjust stock**. Each adjustment requires a reason and cannot take stock below reserved units. **Download Code 128 label** returns that variant's SVG. Search its `SAC…` code or SKU in the variant list. Refunds do not restock physical goods automatically: after a real return is inspected, record the appropriate adjustment explicitly.

No payment-provider calls occur until you explicitly enable/configure test checkout. You do not need to enable checkout to manage local inventory.

## Permanent account environment (separate from the preview)

Keep the preview configuration as-is to share with Tanner. For a durable staging environment, configure these through the host's secure environment settings; **never commit credential values or paste them into chat**:

| Variable | Purpose |
| --- | --- |
| `DJANGO_DEBUG=false` | Production mode; HTTPS and secure cookies. |
| `DJANGO_SECRET_KEY` | Private random 50+ character key; stable across restarts. |
| `SACRATISSIMUM_PREVIEW=false` | Disables disposable demo mode. |
| `DATABASE_URL` | Your durable PostgreSQL connection URL. TLS with server certificate and hostname verification (`verify-full`) is required outside local development. System CAs are used by default; set `PGSSLROOTCERT` to a trusted provider CA file when needed. Verification is not disabled. |
| `ACCOUNTS_ENABLED=true` | Explicit opt-in to collecting customer accounts; production default is false. |
| `SITE_URL` | Your canonical HTTPS site origin, no trailing slash. |
| `DJANGO_ALLOWED_HOSTS` | Exact host(s), if not already supplied by Render's hostname. No wildcard. |
| `EMAIL_HOST`, `EMAIL_PORT` | Your SMTP host and port (587 default). |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Private SMTP credentials where required by the provider. |
| `DEFAULT_FROM_EMAIL` | Your actual verified sending address. |
| `EMAIL_USE_TLS=true` | STARTTLS default. For an SMTPS provider set `EMAIL_USE_SSL=true` (TLS is then disabled). |

The app will not enable production account features without PostgreSQL, SMTP host, a sender, explicit account opt-in, and preview mode off. A PostgreSQL URL combined with disposable preview mode is rejected, so automatic demo seeding cannot accidentally run against your permanent database. External providers were **not configured or tested** because credentials are absent. Select any free allowances deliberately; no paid resources are created by this code and no permanent free service availability is promised.

Run migrations against the intended database. Create your own administrator interactively with `createsuperuser`; no default password exists. On Render Free, if a server shell is unavailable, these management commands can run from your private local environment configured to connect to the same PostgreSQL database. Do not expose connection strings in shared terminal output.

Then sign in at `/account/login/`, visit `/account/security/`, confirm your password, add the private key to a time-based authenticator app and verify a code. Production `/admin/` requires both password and a **fresh** authenticator code; an enrollment code cannot be replayed. Keep a private, tested recovery procedure for loss of the authenticator. Recovery requires trusted operator access, not a public password-only bypass.

## Durable product images

Bundled demo artwork stays in Git/static files. For actual uploaded product photos, configure a durable S3-compatible provider before relying on admin uploads:

- `STORAGE_BUCKET`
- `STORAGE_ENDPOINT_URL` (explicit HTTPS endpoint)
- `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` (private, least-privilege credentials)
- `STORAGE_REGION` (defaults to `us-east-1`; use your provider's value)

Uploads are private by default and use time-limited signed image URLs. Static files still use WhiteNoise. No public `/media/` server is enabled. Without object storage, local media remains development-only and will be lost on ephemeral hosts. Product uploads are limited to JPG/PNG/WebP, 5 MB and 16 megapixels. Do not put private customer documents in the product image area.

## Explicit Stripe test setup

Create your own Stripe account and use its **test/sandbox environment**, never live keys for this version. Configure the business location and Stripe Tax test settings/registrations accurately; software does not decide your tax obligations.

| Variable | Value |
| --- | --- |
| `STRIPE_SECRET_KEY` | Your private `sk_test_…` or restricted `rk_test_…` key with Checkout permissions. |
| `STRIPE_WEBHOOK_SECRET` | Private signing secret for this exact test webhook endpoint. |
| `CHECKOUT_ENABLED` | `true` only when all remaining test settings are ready. Default is false. |
| `STORE_FULFILLMENT` | `shipping` (owner confirmed). |
| `SHIPPING_COUNTRIES` | `US` (default). |
| `SHIPPING_RATE_CENTS` | Your approved non-negative flat fee in cents. **Leave unset until decided.** Zero explicitly means free shipping. |

No publishable key is required for the server-created hosted Checkout redirect. Payment inputs live on Stripe, not this website. No iframe/card form or card-storage file is added.

Configure the Stripe test webhook URL as:

```text
https://YOUR-ASSIGNED-HOST/payments/stripe/webhook/
```

Pin its payload API version to **`2026-09-30.endive`**, matching the installed Stripe 16 SDK. Subscribe to:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.expired`
- `charge.refunded`

Use Stripe's test cards and test addresses; verify tax in the states relevant to your test scenario. No live charges are supported. These remote tests have **not** been performed here: no Stripe key or webhook signing secret was provided.

## Stock/payment recovery and operations

Starting checkout reserves units atomically; it does not reduce physical stock. Expiry is set to 45 minutes. Signed paid notifications reduce both physical and reserved quantities once. Verified expiration/cancellation releases reservations. Stock is not blindly freed just because the browser closes or a request times out: a payment may have succeeded despite a lost response.

The Stripe creation request uses the order UUID as its idempotency key. Retries resume the same order/session. If a payment unexpectedly arrives after a verified release, the order is flagged **needs review** rather than silently overselling. Staff must investigate it in Stripe before fulfillment.

For missed notifications or abandoned/ambiguous checkouts, run with the correct private test environment:

```bash
python manage.py reconcile_payments
```

It checks Stripe's authoritative state before releasing units, recovers lost session IDs by order metadata, and retries unsent confirmation emails. Configure an operator routine/scheduler before relying on the store; no paid cron service is provisioned. Stripe webhook retries remain important. If the provider is unavailable, reservations stay held for safe reconciliation. Receipt email delivery can be retried; SMTP cannot guarantee exactly-once delivery after a connection failure.

Refunds are initiated by an authorized operator in Stripe, not through an unsecured customer refund button. Verified refund events update order status/amount monotonically and do not automatically return units to stock. Physical returns require staff review. Record fulfillment time, carrier, tracking number and an HTTPS tracking link in order admin only after payment is confirmed. Orders marked needs review must be resolved first.

Before accepting real orders, test backup **and restore** of PostgreSQL and media, enable appropriate provider encryption/access restrictions, retain MFA seeds/backups securely, approve business policies and retention procedures, run deployment/security checks and perform an end-to-end Stripe sandbox exercise. Backups cannot be configured without choosing a provider/destination. Live payment support is a separate reviewed activation; changing to a live key currently fails closed.

## Git and secret protection

There is no username/password text file. Django stores salted password hashes in the database; TOTP seeds must be stored securely so codes can be verified, and database backups therefore remain sensitive.

The old tracked `db.sqlite3` contained zero users when inspected. It and this project's compiled Python files were removed from Git tracking while preserving the working-machine copies. `.gitignore` now covers database files/sidecars, environment files, backups and private key files. Existing ignored `local.sqlite3` is not deleted. A merge can remove the old tracked file from another checkout: back up any local changes to it first. Git history still contains the old committed file; adding an ignore rule does not erase history or rotate exposed credentials.

Gunicorn access logs omit request paths/query strings so reset/activation tokens and order URLs are not written to access logs. Error reporting redacts database/storage/email credentials and sensitive form fields. Keep host logs private. HTTPS, secure/HTTP-only cookies, CSRF checks, ownership/permission checks and rate limits are enforced by application configuration, **not** by `.gitignore`.

## Validation

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/verify_render_preview.py
```

Tests exercise password hashing and verification, password-reset/session invalidation, real OTP verification/admin enforcement, authorization/CSRF, inventory constraints and all-or-nothing holds, server-side pricing, duplicate/reordered events, signed webhooks, mismatched totals/currency, refunds, lost-provider-response retries and cancellation. Stripe HTTP requests are mocked; signing verification uses the actual SDK. Browser checks cover responsive account/bag/product forms and add/update/remove behavior. PostgreSQL concurrency, real SMTP, remote object storage and actual Stripe Checkout need integration validation with your chosen providers before enabling public commerce.
