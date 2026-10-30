# Clothing studio — private planning assets

These files do not publish products or appear in the storefront. All concepts are
unapproved regular T-shirts; no hoodies. Supply owned PNG artwork later.

Structure: `audience/collection/product/images/color/front.png` (also `back.png`
and `detail.png`). Use lowercase hyphenated names. Keep transparent backgrounds
when appropriate. Do not duplicate artwork for sizes unless the artwork changes;
use `images/color/size/` only for a genuinely different print. No fake PNG files
are included. Add final dimensions and descriptive alt text to product.json.

Each product.json is a planning record, not an importer. Sizes, prices, fabric,
stock and release dates remain unconfirmed. Adult and kids' sizing are separate.

To publish later: approve the design, upload images in Django admin, create the
size/color variants with confirmed stock, set Adult or Kids, and deliberately
check Published. Enable Preorder interest only to list a real upcoming item on
the interest page. This does not enable paid preorders or reserve inventory.
Never put personal customer data or credentials in this directory.
