"""Versioned identity features. Legacy artifacts must keep using features.py."""
import re

import numpy as np
from scipy.sparse import csr_matrix, hstack

from .features import text_column, overlap_score, token_set

SCHEMA = 'tfidf_pair_v4'


def identity(text):
    capacities = {int(n) * {'mb': 1, 'gb': 1000, 'tb': 1000000}[unit]
                  for n, unit in re.findall(r'\b(\d+)\s*(mb|gb|tb)\b', text)}
    tokens = text.split()
    models = {token for token in tokens
              if re.search(r'[a-z]', token) and re.search(r'\d', token)
              and not re.fullmatch(r'\d+(?:mb|gb|tb|mhz|ghz|hz|mm|cm|inch|in|w|v|mah)', token)}
    for index, (left, right) in enumerate(zip(tokens, tokens[1:])):
        following_unit = index + 2 < len(tokens) and tokens[index + 2] in {'mb', 'gb', 'tb', 'mhz', 'ghz', 'mm', 'cm', 'inch', 'mah'}
        if left.isalpha() and right.isdigit() and not following_unit and left not in {'ram', 'storage', 'size', 'pack', 'of', 'for'}:
            models.add(left + right)
    # Normalize joined/spaced phone identifiers and named generations consistently.
    for generation in re.findall(r'\biphone\s*(\d{1,2}(?:s|c)?|se|xr|xs|x)\b', text):
        models.discard(generation)
        models.add('iphone' + generation)
    accessories = {kind for kind, pattern in [
        ('charger', r'\b(charger|charging cable|power adapter)\b'),
        ('case', r'\b(case|cover|skin)\b'),
        ('bag', r'\b(bag|pouch)\b'),
        ('protector', r'\b(screen protector|tempered glass)\b'),
        ('lens', r'\blens\b')]
        if re.search(pattern, text)}
    kind = next(iter(accessories)) if len(accessories) == 1 else None
    if not accessories:
        kind = next((kind for kind, pattern in [
            ('phone', r'\b(iphone|smartphone|mobile phone)\b'),
            ('camera', r'\b(camera|camcorder)\b'),
            ('laptop', r'\b(laptop|notebook|chromebook)\b'),
            ('watch', r'\b(watch|wristwatch)\b'),
            ('shoe', r'\b(shoe|shoes|sneaker|sneakers|boot|boots)\b')]
            if re.search(pattern, text)), None)
    colors = set(re.findall(r'\b(black|white|silver|gray|grey|blue|red|green|gold|pink|purple)\b', text))
    colors = {'gray' if value == 'grey' else value for value in colors}
    return models, capacities, colors, kind


def pair_features(frame, title_vectorizer, description_vectorizer):
    left = text_column(frame, 'title', 'left')
    right = text_column(frame, 'title', 'right')
    a, b = title_vectorizer.transform(left), title_vectorizer.transform(right)
    ld, rd = text_column(frame, 'description', 'left'), text_column(frame, 'description', 'right')
    lb, rb = text_column(frame, 'brand', 'left'), text_column(frame, 'brand', 'right')
    title_intersection = a.multiply(b)
    description_intersection = description_vectorizer.transform(ld).multiply(description_vectorizer.transform(rd))
    title_cosine = np.asarray(title_intersection.sum(axis=1)).ravel()
    description_cosine = np.asarray(description_intersection.sum(axis=1)).ravel()
    # Unlike the legacy intersection, this explicitly represents words present on only one side.
    difference = abs(a - b)
    rows = []
    for index, (lt, rt) in enumerate(zip(left, right)):
        li, ri = identity(lt), identity(rt)
        brands_known = bool(lb[index] and rb[index])
        row = [title_cosine[index], description_cosine[index],
               overlap_score(token_set(lt), token_set(rt)),
               min(len(lt), len(rt)) / max(len(lt), len(rt)) if lt or rt else 0,
               float(bool(lt) and lt == rt), float(bool(ld[index]) and bool(rd[index])),
               float(brands_known), float(brands_known and lb[index] == rb[index]),
               float(brands_known and lb[index] != rb[index])]
        for x, y in zip(li[:3], ri[:3]):
            known = bool(x and y)
            row.extend([float(known), float(known and x == y),
                        float(known and x.isdisjoint(y)), overlap_score(x, y)])
        lk, rk = li[3], ri[3]
        known = lk is not None and rk is not None
        row.extend([float(known), float(known and lk == rk), float(known and lk != rk)])
        rows.append(row)
    return hstack([title_intersection, description_intersection, difference,
                   csr_matrix(np.asarray(rows, dtype=float))], format='csr')
