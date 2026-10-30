# Clothing

Collections live together here. Kids is a collection, not a second folder tree.

```
clothing/
  faith-edit/              Existing three website demo T-shirts
    most-sacred-tee/images/ivory/front.svg
    walk-in-faith-tee/images/charcoal/front.svg
    abide-tee/images/stone/front.svg
  kids/
    star-and-halo-tee/images/cream/
  sacred-origins/
    cathedral-tee/images/black/
  quiet-faith/
    halo-tee/images/white/
  eternal-bloom/
    botanical-tee/images/cream/
```

For each garment, add `front.png`, `back.png`, and `detail.png` under
`images/color/`. Sizes belong in the product's variants, not duplicate folders;
add a size subfolder only when its artwork differs. PNGs can be transparent.
Empty folders contain `.gitkeep` so Git preserves them.

`product.json` files describe unapproved concepts. They are not imported,
publicly served, or published automatically. Prices and sizes are unconfirmed.
Only the three existing Faith Edit demo image directories are exposed as static
assets, through `STATICFILES_DIRS`. Other planning files stay private.

To launch a real piece: approve its design, create it in Django admin, upload
owned PNGs, enter confirmed size/color variants, and deliberately publish it.
Mark the Audience as Kids for children's garments. No hoodies are planned.
