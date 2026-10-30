# Collections, preorder interest and wholesale

## What is live

- `/kids/`: only published products with Audience set to Kids.
- `/preorders/`: only published, non-demo products with Preorder interest enabled.
  Registers interest only: no deposit, charge, reservation or shipping promise.
- `/wholesale/`: boutique inquiry/application; no automatic approval, wholesale
  pricing, bulk checkout or promised minimums.
- Authorized staff review submissions in admin → Store → Inquiries and mark Reviewed.
  No automatic email is sent. Contact the applicant through your normal business channel.
  Delete inquiries when no longer needed under your business retention policy.

Both forms use existing STORE_FEATURES_ENABLED gating: disabled in disposable
preview; in production require accounts enabled, PostgreSQL, email host and sender
configuration. A disposable SQLite showcase must not collect customer details.
Local development enables forms by default. Form submissions require contact
consent and CSRF protection and have a 60-second session cooldown. This cooldown
is basic duplicate prevention, not a replacement for deployment-level abuse controls.

## Private clothing studio

See `clothing/README.md`. Four T-shirt concepts are organized as JSON planning
records with color image folders. None are imported into the database or exposed
through static/media routes. No sample collection has been published. Add your PNGs
later, approve each garment, and upload approved images through the product admin.
An empty folder in Git needs its `.gitkeep`; remove that file when adding images.

## Update a local checkout (Windows Command Prompt)

Cloud edits must first be committed and merged into the remote `main` branch
using the change/PR workflow. A local pull cannot download uncommitted cloud files.
Then:

```bat
cd /d "C:\Users\Micha\Github\Python_Lab"
git status
git pull --ff-only origin main
cd "MWS\Websites\Sacratissimum"
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

For later local changes, review and commit from the repository root:

```bat
cd /d "C:\Users\Micha\Github\Python_Lab"
git add "MWS/Websites/Sacratissimum"
git diff --cached --stat
git commit -m "Update Sacratissimum collections and clothing assets"
git push origin main
```

If your changes are on another branch, merge them through your normal PR workflow
instead of assuming they are on main. Preserve local changes before pulling.

## Website deployment

Git push updates GitHub, not necessarily the hosted website. The documented Render
service has Auto-Deploy off: after merging to the branch connected to Render,
choose Manual Deploy → Deploy latest commit. Existing build.sh collects static
files; start.sh applies migrations. No new services or payment keys are needed.
Preview keeps forms disabled intentionally. Do not enable paid preorders or claim
wholesale purchasing is ready; confirm pricing, minimums, delivery/refund terms,
payment flow and real stock in a separate implementation first.
