"""Persian text normalization for keyword work. Pure standard library.

The problems this solves, in the order they hit a real keyword list:

1. Arabic letters typed instead of Persian ones (ي vs ی, ك vs ک) —
   the same keyword then counts as two different queries.
2. Missing half-space (نیم‌فاصله): "می روم", "کتاب ها" instead of
   "می‌روم", "کتاب‌ها". Search Console exports are full of these.
3. Diacritics and tatweel (ـ) pasted from Arabic sources.
4. Arabic-Indic digits (١٢٣) mixed with Persian digits (۱۲۳).
5. Stray punctuation and doubled whitespace.

Everything here is deterministic string work — no model, no network.
"""

from __future__ import annotations

import re
import unicodedata

ZWNJ = "\u200c"  # zero-width non-joiner — the Persian half-space
ZWJ = "\u200d"

# Arabic letters that Persian keyboards/users constantly mix in.
_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",  # Arabic yeh -> Persian yeh
        "ك": "ک",  # Arabic kaf -> Persian kaf
        "ة": "ه",  # teh marbuta -> heh
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
    }
)

# Arabic-Indic digits -> Persian digits (Latin digits are left alone).
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")

# Arabic diacritics (tanwin, harakat) + tatweel (kashida).
_DIACRITICS = re.compile(r"[\u064b-\u0652\u0670\u0640]")

_WHITESPACE = re.compile(r"\s+")

# Edge punctuation stripped from a keyword (kept inside the phrase).
_EDGE_PUNCT = " \t\"'«»()[]{}،؛؟!?.:;,"

# Verb prefixes that take a half-space before the verb.
_PREFIXES = ("نمی", "می")

# Suffixes that take a half-space after the word they attach to.
_SUFFIXES = (
    "های",
    "ترین",
    "ها",
    "تر",
    "مان",
    "تان",
    "شان",
    "ام",
    "ات",
    "اش",
)


def _join_affixes(tokens: list[str]) -> list[str]:
    """Re-attach detached prefixes/suffixes with a half-space.

    "می روم" -> "می‌روم", "کتاب ها" -> "کتاب‌ها",
    "خانه ی من" -> "خانه‌ی من".
    """
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _PREFIXES and i + 1 < len(tokens):
            out.append(tok + ZWNJ + tokens[i + 1])
            i += 2
            continue
        if tok == "ی" and out:  # ezafe: "خانه ی" -> "خانه‌ی"
            out[-1] = out[-1] + ZWNJ + "ی"
            i += 1
            continue
        if tok in _SUFFIXES and out:
            out[-1] = out[-1] + ZWNJ + tok
            i += 1
            continue
        out.append(tok)
        i += 1
    return out


def normalize(text: str) -> str:
    """Normalize one Persian keyword (or any short Persian text).

    >>> normalize("خريد كتاب هاي خوب")
    'خرید کتاب‌های خوب'
    >>> normalize("می روم به مدرسه‌ی خوب")
    'می‌روم به مدرسه‌ی خوب'
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_ARABIC_TO_PERSIAN)
    text = text.translate(_DIGITS)
    text = _DIACRITICS.sub("", text)
    text = text.replace(ZWJ, "")
    text = _WHITESPACE.sub(" ", text).strip(_EDGE_PUNCT)
    if not text:
        return ""
    tokens = _join_affixes(text.split(" "))
    return " ".join(tokens)


def normalize_keyword(keyword: str) -> str:
    """Alias kept for readability at call sites."""
    return normalize(keyword)


def tokenize(text: str) -> list[str]:
    """Normalize, then split into tokens."""
    normalized = normalize(text)
    return normalized.split(" ") if normalized else []


def comparison_key(word: str) -> str:
    """Token form used for equality/comparison: half-space-insensitive.

    "لپ‌تاپ" and "لپتاپ" are the same word for clustering purposes,
    so the comparison key drops the ZWNJ.
    """
    return normalize(word).replace(ZWNJ, "")
