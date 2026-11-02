"""Optional Render build step: fetch team-owned artifacts and verify their hashes."""

import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def download(name, target):
    url = os.getenv(f"{name}_URL")
    if not url:
        print(f"{name}: no download configured; existing files left unchanged.")
        return
    checksum = os.getenv(f"{name}_SHA256", "").lower()
    if len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
        raise ValueError(f"Set {name}_SHA256 to the trusted file hash before downloading.")
    if urlsplit(url).scheme != "https":
        raise ValueError("Artifact downloads require HTTPS.")
    if target.exists() and file_hash(target) == checksum:
        print(f"{name}: verified existing file.")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with urlopen(url, timeout=120) as response:
            if urlsplit(response.url).scheme != "https":
                raise ValueError("Artifact redirect must use HTTPS.")
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as file:
                temporary = Path(file.name)
                while chunk := response.read(1024 * 1024):
                    file.write(chunk)
        if file_hash(temporary) != checksum:
            raise ValueError(f"{name}: downloaded file checksum does not match.")
        if name == "DATABASE":
            with sqlite3.connect(temporary.resolve().as_uri() + "?mode=ro", uri=True) as conn:
                if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Downloaded database failed SQLite integrity checking.")
                conn.execute("SELECT id, title FROM products LIMIT 1").fetchall()
                conn.execute("SELECT rowid FROM product_search LIMIT 1").fetchall()
        temporary.replace(target)
        print(f"{name}: downloaded and verified.")
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def file_hash(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    download("MODEL", Path(os.getenv("PRODUCTMATCH_MODEL_DIR", ROOT / "models")) / "svm_small_v3.joblib")
    download("DATABASE", Path(os.getenv("PRODUCTMATCH_DATA_DIR", ROOT / "data")) / "products.db")


if __name__ == "__main__":
    main()
