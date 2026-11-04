
import argparse
import gzip
import json
import re
from pathlib import Path

from website.database import connect, initialize, DB_PATH

ROOT = Path(__file__).resolve().parent.parent

SOURCE = (
    ROOT
    / "data"
    / "offers_corpus_all_v2_non_norm.json.gz"
)


def first_value(record, *keys):
    for key in keys:
        value = record.get(key)

        if value is not None and value != "":
            return value

    return None


def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)

    value = str(value)

    # Remove language tags such as @en, @de, @nl
    value = re.sub(r"@[a-z]{2}(?=\W|$)", "", value)

    # Remove replacement characters from corrupted text
    value = value.replace("\ufffd", "")

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def price_number(value):
    if isinstance(value, dict):
        value = first_value(
            value, "amount", "value", "price"
        )

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value) if 0 <= value < 1e9 else None

    match = re.search(
        r"\d+(?:\.\d+)?",
        str(value).replace(",", "")
    )

    if not match:
        return None

    return float(match.group())


def normalize(record, line_number):
    if not isinstance(record, dict):
        return None

    title = clean_text(first_value(
        record,
        "title",
        "name",
        "productTitle",
        "product_name",
        "productName"
    ))

    if not title:
        return None

    brand = clean_text(first_value(
        record,
        "brand",
        "manufacturer",
        "brandName"
    ))

    description = clean_text(first_value(
        record,
        "description",
        "desc",
        "productDescription",
        "shortDescription",
        "specTableContent",
        "keyValuePairs"
    ))

    category = clean_text(
        record.get("category")
    )

    cluster_id = clean_text(
        record.get("cluster_id")
    )

    identifiers = json.dumps(
        record.get("identifiers") or [],
        ensure_ascii=False
    )

    raw_price = first_value(
        record,
        "price",
        "priceValue",
        "price_value",
        "salePrice",
        "offerPrice"
    )

    currency = clean_text(first_value(
        record,
        "currency",
        "priceCurrency",
        "currencyCode"
    ))

    if isinstance(raw_price, dict) and not currency:
        currency = clean_text(first_value(
            raw_price,
            "currency",
            "currencyCode"
        ))

    seller = clean_text(first_value(
        record,
        "shop",
        "seller",
        "merchant",
        "source",
        "domain",
        "site",
        "vendor"
    ))

    url = clean_text(first_value(
        record,
        "url",
        "productUrl",
        "productURL",
        "link",
        "product_url"
    ))

    source_id = clean_text(first_value(
        record,
        "id",
        "offer_id",
        "offerId",
        "productId"
    ))

    if not source_id:
        source_id = f"line:{line_number}"

    return (
        source_id[:300],
        cluster_id,
        category[:300],
        identifiers,
        title[:2000],
        brand[:500],
        description[:12000],
        price_number(raw_price),
        currency[:30],
        seller[:300],
        url[:2000]
    )


def records():
    with gzip.open(
        SOURCE,
        "rt",
        encoding="utf-8-sig",
        errors="replace"
    ) as file:

        for line_number, line in enumerate(file, 1):

            if not line.strip():
                continue

            try:
                yield line_number, json.loads(line)

            except json.JSONDecodeError:
                print(
                    f"Skipping invalid JSON at line {line_number}"
                )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=50000
    )

    parser.add_argument(
        "--inspect",
        action="store_true"
    )

    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"Dataset not found: {SOURCE}")
        return

    if args.limit < 1:
        print("Limit must be greater than zero.")
        return

    if args.inspect:
        try:
            line, record = next(records())

            print("Original record:")
            print(json.dumps(record, indent=2)[:5000])

            print("\nNormalized record:")
            print(normalize(record, line))

        except StopIteration:
            print("Dataset is empty.")

        return

    conn = connect()
    initialize(conn)

    batch = []
    processed = 0

    insert_sql = """
        INSERT OR IGNORE INTO products
        (
            source_id,
            cluster_id,
            category,
            identifiers,
            title,
            brand,
            description,
            price,
            currency,
            seller,
            url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        for line, record in records():
            processed += 1

            product = normalize(record, line)

            if product:
                batch.append(product)

            if len(batch) >= 1000:
                conn.executemany(insert_sql, batch)
                conn.commit()
                batch.clear()

            if processed % 10000 == 0:
                print(
                    f"Processed {processed:,} records"
                )

            if processed >= args.limit:
                break

        if batch:
            conn.executemany(insert_sql, batch)
            conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        print(
            f"\nFinished. Database contains "
            f"{count:,} products."
        )

        print(f"Saved to: {DB_PATH}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
