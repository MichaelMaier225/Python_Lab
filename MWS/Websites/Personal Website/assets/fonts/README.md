# Locally hosted typefaces

- Manrope variable, weights 200–800: https://github.com/google/fonts/tree/main/ofl/manrope
- Instrument Serif Italic, weight 400: https://github.com/google/fonts/tree/main/ofl/instrumentserif

Downloaded from the official Google Fonts repository with TLS verification. Both are distributed under the SIL Open Font License 1.1; the complete copyright notices and licenses are included alongside the files.

The original TTF files were converted to Latin WOFF subsets using FontTools. Coverage includes U+0020–017F, U+2000–206F, the euro sign, and four directional arrows. Layout features and font names are retained. Manrope keeps its variable weight axis. CSS declares local @font-face rules with font-display: swap; no network font provider is needed by the deployed site.
