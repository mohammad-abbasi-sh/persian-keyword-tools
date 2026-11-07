"""Persian stemming for keyword work.

Two engines:

* ``light`` — a small, conservative rule-based stemmer (this module).
  It only strips what is safe to strip in a keyword context: verb
  prefixes (می‌/نمی‌), plural and comparative suffixes
  (ها/های/تر/ترین/ان/یان) and possessive endings. It deliberately does
  NOT strip verb endings (خرید must never become خر), which is why it
  stays short.
* ``hazm`` — Hazm's Stemmer when the ``hazm`` package is installed.
  Stronger (handles verb conjugations), but an extra dependency.

``stem(word)`` uses Hazm when available and falls back to the light
stemmer otherwise, so the same code runs with or without Hazm.
"""

from __future__ import annotations

from .normalize import ZWNJ, normalize

# Words that end in "ان" but are NOT plurals — never strip them.
# (ایران/تهران/باران are caught by the "ران" rule below; ارزان is not,
# so it is listed explicitly.)
_FALSE_PLURAL_AN = frozenset({"ارزان"})

# Longest first — order matters ("های" must win over "ها").
_SUFFIXES = (
    "ترین",
    "های",
    "ها",
    "تر",
    "یان",
    "ان",
    "مان",
    "تان",
    "شان",
    "ام",
    "ات",
    "اش",
)

_PREFIXES = ("نمی" + ZWNJ, "می" + ZWNJ)

_hazm_stemmer = None
_hazm_tried = False


def hazm_available() -> bool:
    """True when the hazm package can be imported."""
    try:
        import hazm  # noqa: F401

        return True
    except ImportError:
        return False


def _get_hazm_stemmer():
    global _hazm_stemmer, _hazm_tried
    if _hazm_tried:
        return _hazm_stemmer
    _hazm_tried = True
    try:
        from hazm import Stemmer

        _hazm_stemmer = Stemmer()
    except ImportError:
        _hazm_stemmer = None
    return _hazm_stemmer


def light_stem(word: str) -> str:
    """Conservative rule-based stem of one normalized word.

    >>> light_stem("کتاب‌ها")
    'کتاب'
    >>> light_stem("خوب‌ترین")
    'خوب'
    >>> light_stem("می‌روم")
    'روم'
    >>> light_stem("خرید")  # verb endings are never stripped
    'خرید'
    """
    word = normalize(word)
    if not word:
        return ""
    for prefix in _PREFIXES:
        if word.startswith(prefix) and len(word) > len(prefix):
            word = word[len(prefix):]
            break
    # Trailing ezafe "‌ی" (e.g. "خانه‌ی" -> "خانه").
    if word.endswith(ZWNJ + "ی") and len(word) > 2:
        word = word[: -len(ZWNJ + "ی")]
    for suffix in _SUFFIXES:
        if word.endswith(suffix):
            # "ان" is not always a plural: ایران، تهران، ارزان، باران
            # are single words, not "ایر/تهر/ارز/بار" + "ان".
            if suffix == "ان" and (
                word in _FALSE_PLURAL_AN or word.endswith("ران")
            ):
                break
            candidate = word[: -len(suffix)]
            # "کتاب‌ها" is کتاب + ZWNJ + ها — drop the orphan half-space.
            candidate = candidate.rstrip(ZWNJ)
            # Never strip down to a 1–2 letter stub: "رمان" is a noun,
            # not "رم" + "ان". Real plural stems keep >= 3 letters.
            if len(candidate) >= 3:
                word = candidate
            break
    return word


def hazm_stem(word: str) -> str:
    """Stem one word with Hazm. Raises ImportError when Hazm is missing."""
    stemmer = _get_hazm_stemmer()
    if stemmer is None:
        raise ImportError(
            "hazm is not installed — pip install hazm, "
            "or use stem(word, engine='light')"
        )
    return stemmer.stem(normalize(word))


def stem(word: str, engine: str = "auto") -> str:
    """Stem one word.

    engine: "auto" (Hazm when installed, else light), "hazm", "light".
    """
    if engine == "light":
        return light_stem(word)
    if engine == "hazm":
        return hazm_stem(word)
    if engine != "auto":
        raise ValueError(f"unknown engine: {engine!r} (auto/hazm/light)")
    stemmer = _get_hazm_stemmer()
    if stemmer is not None:
        return stemmer.stem(normalize(word))
    return light_stem(word)
