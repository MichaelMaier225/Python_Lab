"""Feature functions copied from random_forest.ipynb; do not change training semantics."""
import math
import string
from pathlib import Path

import pandas as pd

def tokenize(words):
    if isinstance(words, float):
        if words != words:
            return []
    words = str(words)
    words = words.replace('&amp;', '')
    words = words.replace('&reg;', '')
    words = words.replace('&quot;', '')
    words = words.replace('\t', ' ')
    words = words.replace('\n', ' ')
    return words.lower().translate(str.maketrans('', '', string.punctuation)).split()

def preprocess_string(words, stop_words):
    if isinstance(words, float):
        if words != words:
            return words
    word_list = tokenize(words)
    word_list_stopwords_removed = [x for x in word_list if x not in stop_words]
    return ' '.join(word_list_stopwords_removed)

# Similarity score formulas 
# https://github.com/anhaidgroup/py_entitymatching/blob/master/py_entitymatching/feature/simfunctions.py
def _levenshtein(s1, s2):
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1, 1):
            cur = [i]
            for j, c2 in enumerate(s2, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (c1 != c2)))
            prev = cur
        return float(prev[-1])

def lev_dist(s1, s2):
    if s1 == s2:
        return 0.0
    return _levenshtein(s1, s2)

def lev_sim(s1, s2):
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1 - (lev_dist(s1, s2) / max_len)

def _jaro_core(s1, s2):
    len1, len2 = len(s1), len(s2)
    search_range = max(len1, len2) // 2 - 1
    if search_range < 0:
        search_range = 0
    flags1 = [False] * len1
    flags2 = [False] * len2
    common = 0
    for i in range(len1):
        low = i - search_range if i > search_range else 0
        high = i + search_range if i + search_range < len2 else len2 - 1
        ch = s1[i]
        for j in range(low, high + 1):
            if not flags2[j] and s2[j] == ch:
                flags1[i] = flags2[j] = True
                common += 1
                break
    if common == 0:
        return 0.0
    trans = 0
    k = 0
    for i in range(len1):
        if flags1[i]:
            j = k
            while j < len2:
                if flags2[j]:
                    k = j + 1
                    break
                j += 1
            if s1[i] != s2[j]:
                trans += 1
    trans = trans // 2
    common = float(common)
    return (common / len1 + common / len2 + (common - trans) / common) / 3.0

def _jaro_winkler_core(s1, s2):
    score = _jaro_core(s1, s2)
    j = min(len(s1), len(s2), 4)
    i = 0
    while i < j and s1[i] == s2[i] and s1[i]:
        i += 1
    if i:
        score += i * 0.1 * (1 - score)
    return score

def jaro_winkler(s1, s2):
    if len(s1) == 0 or len(s2) == 0:
        return 0
    return _jaro_winkler_core(s1, s2)
def needleman_wunsch(s1, s2, gap_cost=1.0):
    n, m = len(s1), len(s2)
    prev = [-(j * gap_cost) for j in range(m + 1)]
    for i in range(1, n + 1):
        cur = [-(i * gap_cost)] + [0.0] * m
        c1 = s1[i - 1]
        for j in range(1, m + 1):
            match = prev[j - 1] + (1.0 if c1 == s2[j - 1] else 0.0)
            cur[j] = max(match, prev[j] - gap_cost, cur[j - 1] - gap_cost)
        prev = cur
    return float(prev[m])
def smith_waterman(s1, s2, gap_cost=1.0):
    n, m = len(s1), len(s2)
    best = 0.0
    prev = [0.0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0.0] * (m + 1)
        c1 = s1[i - 1]
        for j in range(1, m + 1):
            match = prev[j - 1] + (1.0 if c1 == s2[j - 1] else 0.0)
            v = max(0.0, match, prev[j] - gap_cost, cur[j - 1] - gap_cost)
            cur[j] = v
            if v > best:
                best = v
        prev = cur
    return best

def jaccard(arr1, arr2):
    if arr1 == arr2:
        return 1.0
    if len(arr1) == 0 or len(arr2) == 0:
        return 0
    s1, s2 = set(arr1), set(arr2)
    return float(len(s1 & s2)) / float(len(s1 | s2))
def cosine(arr1, arr2):
    if arr1 == arr2:
        return 1.0
    if len(arr1) == 0 or len(arr2) == 0:
        return 0
    s1, s2 = set(arr1), set(arr2)
    return float(len(s1 & s2)) / (math.sqrt(float(len(s1))) * math.sqrt(float(len(s2))))
def monge_elkan(arr1, arr2):
    if arr1 == arr2:
        return 1.0
    if len(arr1) == 0 or len(arr2) == 0:
        return 0
    total = 0.0
    for a in arr1:
        best = float('-inf')
        for b in arr2:
            v = jaro_winkler(a, b)
            if v > best:
                best = v
        total += best
    return total / float(len(arr1))

# Tokening
# https://github.com/anhaidgroup/py_entitymatching/blob/master/py_entitymatching/feature/tokenizers.py
def tok_qgram3(s):
    s = '##' + s + '$$'
    if len(s) < 3:
        return []
    return [s[i:i + 3] for i in range(len(s) - 2)]
def tok_delim_space(s):
    return [t for t in s.split(' ') if t]

TOKENIZERS = {'qgm_3': tok_qgram3, 'dlm_dc0': tok_delim_space}
SIM_FUNCS = {'lev_dist': lev_dist, 'lev_sim': lev_sim, 'jaro_winkler': jaro_winkler,
    'needleman_wunsch': needleman_wunsch, 'smith_waterman': smith_waterman,
    'jaccard': jaccard, 'cosine': cosine, 'monge_elkan': monge_elkan}

def extract_feature_vecs(pairs, features):
    """pairs has attr_left attr_right"""
    out = {}
    cache = {}
    for name, attr, sim, tok in features:
        left = pairs[attr + '_left'].tolist()
        right = pairs[attr + '_right'].tolist()
        fn = SIM_FUNCS[sim]
        if tok:
            key = (attr, tok)
            if key not in cache:
                t = TOKENIZERS[tok]
                cache[key] = ([t(x) for x in left], [t(x) for x in right])
            left, right = cache[key]
        elif sim in ('monge_elkan',):
            left = [[x] for x in left]
            right = [[x] for x in right]
        out[name] = [fn(a, b) for a, b in zip(left, right)]
    return pd.DataFrame(out, index=pairs.index)


STOP_WORDS = [word.lower().translate(str.maketrans('', '', string.punctuation))
              for word in Path(__file__).with_name('stopwords_english.txt').read_text().splitlines()]


def pair_features(pairs, definitions, columns):
    frame = pairs.copy()
    for attr in ['title', 'description', 'brand', 'specTableContent']:
        for side in ['left', 'right']:
            name = f'{attr}_{side}'
            values = frame[name] if name in frame else pd.Series('', index=frame.index)
            values = values.fillna('').apply(preprocess_string, args=(STOP_WORDS,))
            frame[name] = values.where(~values.isin(['', 'nan', 'null']), '').fillna('').astype(str)
    return extract_feature_vecs(frame, definitions)[columns]
