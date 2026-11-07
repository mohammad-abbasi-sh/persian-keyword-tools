"""Persian keyword tools: normalize, stem, dedupe and cluster Persian keywords.

Built for Persian SEO work: keyword lists exported from Search Console,
keyword planners or scraped SERPs are messy — Arabic letters mixed with
Persian ones, missing half-spaces (نیم‌فاصله), duplicate spellings of the
same phrase. This package cleans them up with pure-stdlib code, and uses
Hazm when it is installed for heavier stemming.

Modules:
    normalize  — Persian text normalization (ی/ک, half-space, diacritics)
    stem       — light rule-based stemmer + Hazm stemmer when available
    cluster    — token-overlap clustering of keyword lists
"""

from .cluster import cluster_keywords, dedupe_keywords, jaccard
from .normalize import normalize, normalize_keyword, tokenize
from .stem import hazm_available, light_stem, stem

__all__ = [
    "normalize",
    "normalize_keyword",
    "tokenize",
    "light_stem",
    "stem",
    "hazm_available",
    "cluster_keywords",
    "dedupe_keywords",
    "jaccard",
]

__version__ = "0.1.0"
