"""Content-based asset URLs keep CSS/JS fresh after a Git pull and restart."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path


@lru_cache(maxsize=1)
def _asset_version():
    root = Path(__file__).parent / "static" / "store"
    digest = sha256()
    for filename in ("css/site.css", "js/site.js"):
        digest.update((root / filename).read_bytes())
    return digest.hexdigest()[:12]


def asset_version(request):
    return {"asset_version": _asset_version()}
