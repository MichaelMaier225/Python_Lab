# Maier Web Solutions

Static marketing website for a Louisiana-based small-business web design service.

## Local preview

From this directory, run:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000` in a browser. No build step or package installation is required.

## Project structure

- `index.html` — homepage, sections, and pricing estimator markup.
- `styles.css` — core site styles.
- `script.js` — navigation, pricing, portfolio preview, and page interactions.
- `theme-light.css`, `theme-contrast.css`, `scale-refinement.css` — visual theme refinements.
- `pricing-readable.css`, `readability-fix.css` — pricing and text contrast improvements.
- `portfolio-upgrade.css`, `portfolio-navigation-polish.css`, `portfolio-upgrade.js` — interactive portfolio styling and behavior.
- `hero-slideshow.css`, `hero-slideshow.js` — rotating website demo in the hero.
- `demo-*.html` — fictional website examples, **not actual client work**.
- `terms.html`, `privacy.html` — public-facing policies.
- `Client_Agreement_Template.txt` — agreement draft; seek local legal review before use.

## Pricing

| Package | Setup | Required managed care | Included minor edits |
| --- | --- | --- | --- |
| Starter launch offer (first three qualifying clients) | $100 | $20/month or $200/year | Up to 1 hour/month |
| Starter regular | $130 | $20/month or $200/year | Up to 1 hour/month |
| Business | From $349 | $30/month or $300/year | Up to 2 hours/month |

The first month of care is paid at launch. Setup requires a 50% deposit, with the remainder due after approval and before launch. Customers can cancel managed care and request transfer of their paid site files; hosted service ends after the paid period and appropriate notice. New pages and major changes are separately quoted.

## Publishing checklist

1. Upload all files together to the site root, including any existing `assets/` directory.
2. Verify the domain, contact links, images, pricing estimator, and demo links.
3. Check desktop and mobile layouts and the expanded FAQ text.
4. Confirm the latest terms and agreement match your actual hosting, billing, and cancellation practices.
5. Test the deployed site before directing customers to it.

**Assets:** This archive does not include the original `assets/` directory. Preserve the existing branding and image files from your deployed project. Some backgrounds and demo photos require an internet connection.

**Billing:** The pricing calculator is informational; it does not collect payments or create subscriptions.
