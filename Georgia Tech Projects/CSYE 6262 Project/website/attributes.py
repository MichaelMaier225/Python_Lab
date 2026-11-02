"""Independent observations, not an explanation of the classifier's weights."""

import re


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def attributes(product):
    text = f"{product.get('title', '')} {product.get('description', '')}"
    # Require an explicit label. Do not guess whether an unlabeled capacity is RAM or storage.
    result = {"Brand": product.get("brand") or None}
    for label, pattern in {
        "Model": r"\bmodel\s*(?:number|no\.?)?\s*[:#]\s*([\w-]+)",
        "RAM": r"\b(\d+(?:\.\d+)?\s*(?:GB|MB|TB))\s*(?:of\s+)?RAM\b",
        "Storage": r"\b(\d+(?:\.\d+)?\s*(?:GB|MB|TB))\s*(?:SSD|HDD|storage)\b",
        "Color": r"\bcolou?r\s*:\s*(black|white|silver|gray|grey|blue|red|green|gold)\b",
    }.items():
        found = [m.group(1) for m in re.finditer(pattern, text, re.I)]
        values = list(dict.fromkeys(found))
        # Multiple incompatible values could describe variants or accessories.
        unambiguous = len({comparable(label, value) for value in values}) == 1
        result[label] = values[0] if unambiguous else None
    return result


def comparable(label, value):
    value = normalize(value)
    if label in {"RAM", "Storage"}:
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(MB|GB|TB)", value, re.I)
        if match:
            return float(match[1]) * {"mb": 1, "gb": 1000, "tb": 1000000}[match[2].lower()]
    if label == "Color":
        return value.replace("grey", "gray")
    if label == "Model":
        return re.sub(r"[\s-]", "", value)
    return value


def compare_attributes(a, b):
    left, right = attributes(a), attributes(b)
    return [{"attribute": label, "a": left[label], "b": right[label],
             "status": "unknown" if not left[label] or not right[label] else (
                 "match" if comparable(label, left[label]) == comparable(label, right[label]) else "conflict")}
            for label in left]
