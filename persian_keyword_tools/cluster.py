"""Keyword clustering and deduplication. Pure standard library.

Approach: two normalized keywords belong together when their stemmed
token sets overlap enough. No embeddings, no API — this runs on a plain
keyword list in milliseconds and every grouping is explainable: it can
be traced back to shared tokens.

Two Persian-specific details:

* Generic intent words (خرید، قیمت، بهترین، …) are ignored for
  similarity — otherwise every "خرید X" would cluster with every
  other "خرید Y". They stay in the keyword text, they just don't
  count as topic evidence.
* Spacing variants are handled by also comparing concatenations of
  adjacent tokens, so "لپ تاپ" still matches "لپ‌تاپ".

Deduplication is the exact-match half of the same idea: two spellings
that normalize to the same string are one keyword.
"""

from __future__ import annotations

from .normalize import comparison_key, normalize, tokenize
from .stem import light_stem

# Generic intent/qualifier words: real words, but they say nothing
# about the TOPIC, so they must not glue unrelated clusters together.
STOPWORDS = frozenset(
    {
        "خرید",
        "قیمت",
        "بهترین",
        "ارزان",
        "گران",
        "آنلاین",
        "رایگان",
        "جدید",
        "فروش",
        "سفارش",
        "دانلود",
    }
)


def keyword_tokens(keyword: str) -> frozenset[str]:
    """Stemmed, half-space-insensitive topic tokens of a keyword."""
    return frozenset(
        light_stem(comparison_key(token))
        for token in tokenize(keyword)
        if light_stem(comparison_key(token)) not in STOPWORDS
    )


def expanded_tokens(keyword: str) -> frozenset[str]:
    """Topic tokens plus concatenations of adjacent token pairs.

    The pair forms let "لپ تاپ" (two tokens) match "لپ‌تاپ" (one).
    """
    tokens = [tok for tok in tokenize(keyword)]
    stems = [
        light_stem(comparison_key(tok))
        for tok in tokens
    ]
    stems = [s for s in stems if s not in STOPWORDS]
    pairs = {"".join(stems[i : i + 2]) for i in range(len(stems) - 1)}
    return frozenset(stems) | pairs


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity of two token sets (0.0–1.0)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """Overlap coefficient: shared tokens / size of the smaller set."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def similarity(a: str, b: str) -> float:
    """Similarity of two keywords (0.0–1.0).

    The max of token-set Jaccard and expanded-set overlap: Jaccard
    keeps big clusters honest, overlap catches spacing variants.
    """
    return max(
        jaccard(keyword_tokens(a), keyword_tokens(b)),
        overlap(expanded_tokens(a), expanded_tokens(b)),
    )


def dedupe_keywords(keywords: list[str]) -> dict[str, list[str]]:
    """Group raw spellings by their normalized form.

    Returns {normalized: [raw spellings in first-seen order]}.
    A group with more than one spelling is a duplicate you were
    counting twice.
    """
    groups: dict[str, list[str]] = {}
    for keyword in keywords:
        key = normalize(keyword)
        if not key:
            continue
        groups.setdefault(key, []).append(keyword)
    return groups


def cluster_keywords(
    keywords: list[str], threshold: float = 0.30
) -> list[dict]:
    """Greedy agglomerative clustering of keywords by token overlap.

    Each keyword joins the existing cluster it is most similar to
    (max similarity against any member) when that similarity is at
    least ``threshold``; otherwise it starts a new cluster. Clusters
    are returned biggest-first; the label is the shortest normalized
    keyword in the cluster (the canonical form).

    >>> clusters = cluster_keywords(["خرید کفش ورزشی", "کفش ورزشی ارزان",
    ...                              "آموزش زبان آلمانی"], threshold=0.30)
    >>> len(clusters)
    2
    >>> clusters[0]["label"]
    'خرید کفش ورزشی'
    """
    cleaned = [kw for kw in keywords if normalize(kw)]

    clusters: list[dict] = []  # each: {"members": [...]}
    for keyword in cleaned:
        best_idx = -1
        best_sim = 0.0
        for idx, cluster in enumerate(clusters):
            sim = max(similarity(keyword, other) for other in cluster["members"])
            if sim > best_sim:
                best_sim = sim
                best_idx = idx
        if best_idx >= 0 and best_sim >= threshold:
            clusters[best_idx]["members"].append(keyword)
        else:
            clusters.append({"members": [keyword]})

    result = []
    for cluster in clusters:
        normalized = [normalize(kw) for kw in cluster["members"]]
        label = min(normalized, key=len)
        result.append(
            {
                "label": label,
                "size": len(cluster["members"]),
                "keywords": sorted(set(normalized)),
            }
        )
    result.sort(key=lambda c: (-c["size"], c["label"]))
    return result
