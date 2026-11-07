"""Tests for persian-keyword-tools.

Run with either:
    python -m pytest tests/ -q
    python -m unittest discover -s tests -v

The doctests in the package modules are part of the suite too:
    python -m pytest --doctest-modules persian_keyword_tools/ -q
    # or: python -c "import doctest, persian_keyword_tools.cluster as m; doctest.testmod(m)"
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persian_keyword_tools import (  # noqa: E402
    cluster_keywords,
    dedupe_keywords,
    jaccard,
    light_stem,
    normalize,
    stem,
    tokenize,
)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "sample-keywords.csv"


def read_sample() -> list[str]:
    return [
        line.strip()
        for line in SAMPLE.read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    ]


class TestNormalize(unittest.TestCase):
    def test_arabic_letters_become_persian(self):
        self.assertEqual(normalize("خريد كتاب"), "خرید کتاب")
        self.assertEqual(normalize("مدرسه‌ی خوب"), "مدرسه‌ی خوب")

    def test_half_space_joined(self):
        self.assertEqual(normalize("می روم به مدرسه"), "می‌روم به مدرسه")
        self.assertEqual(normalize("کتاب ها"), "کتاب‌ها")
        self.assertEqual(normalize("خانه ی من"), "خانه‌ی من")
        self.assertEqual(normalize("خوب تر"), "خوب‌تر")
        self.assertEqual(normalize("خوب ترین"), "خوب‌ترین")

    def test_diacritics_and_tatweel_removed(self):
        self.assertEqual(normalize("مُدرسه"), "مدرسه")
        self.assertEqual(normalize("کتـــاب"), "کتاب")

    def test_arabic_indic_digits_become_persian(self):
        self.assertEqual(normalize("قیمت ١٢٣"), "قیمت ۱۲۳")
        # Latin digits are left alone.
        self.assertEqual(normalize("مدل 2024"), "مدل 2024")

    def test_whitespace_and_punctuation(self):
        self.assertEqual(normalize("  خرید   کفش  "), "خرید کفش")
        self.assertEqual(normalize("«خرید کفش»؟"), "خرید کفش")

    def test_empty(self):
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize("   "), "")

    def test_tokenize(self):
        self.assertEqual(tokenize("خرید کفش ورزشی"), ["خرید", "کفش", "ورزشی"])


class TestStem(unittest.TestCase):
    def test_light_stem_plurals_and_comparatives(self):
        self.assertEqual(light_stem("کتاب‌ها"), "کتاب")
        self.assertEqual(light_stem("کتاب‌های"), "کتاب")
        self.assertEqual(light_stem("خوب‌ترین"), "خوب")
        self.assertEqual(light_stem("دانشجویان"), "دانشجو")

    def test_light_stem_verb_prefix(self):
        self.assertEqual(light_stem("می‌روم"), "روم")
        self.assertEqual(light_stem("نمی‌خواهم"), "خواهم")

    def test_light_stem_never_mangles_nouns(self):
        # "رمان" is a noun, not "رم" + "ان"; "خرید" is not "خر" + "ید".
        self.assertEqual(light_stem("رمان"), "رمان")
        self.assertEqual(light_stem("خرید"), "خرید")
        self.assertEqual(light_stem("زبان"), "زبان")
        # "ان" is not always a plural: ایران/تهران/ارزان/باران are words.
        self.assertEqual(light_stem("ارزان"), "ارزان")
        self.assertEqual(light_stem("ایران"), "ایران")
        self.assertEqual(light_stem("تهران"), "تهران")

    def test_stem_auto_falls_back_without_hazm(self):
        # Works whether or not hazm is installed in this environment.
        self.assertEqual(stem("کتاب‌ها", engine="light"), "کتاب")
        self.assertIn(stem("کتاب‌ها"), ("کتاب",))


class TestCluster(unittest.TestCase):
    def test_jaccard(self):
        self.assertEqual(jaccard(frozenset({"a", "b"}), frozenset({"a", "b"})), 1.0)
        self.assertEqual(jaccard(frozenset({"a"}), frozenset({"b"})), 0.0)
        self.assertAlmostEqual(jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})), 1 / 3)

    def test_dedupe_collapses_spelling_variants(self):
        groups = dedupe_keywords(["خرید کتاب", "خرید كتاب", "کتاب‌های خوب", "کتاب های خوب"])
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups["خرید کتاب"]), 2)
        self.assertEqual(len(groups["کتاب‌های خوب"]), 2)

    def test_sample_clusters_into_four_topics(self):
        clusters = cluster_keywords(read_sample(), threshold=0.30)
        labels = {c["label"] for c in clusters}
        self.assertEqual(len(clusters), 4)
        self.assertEqual({c["size"] for c in clusters}, {5, 5, 5, 6})
        self.assertIn("خرید کفش ورزشی", labels)
        self.assertIn("دوره زبان آلمانی", labels)
        self.assertIn("لپ‌تاپ گیمینگ", labels)
        self.assertIn("خرید کتاب", labels)

    def test_spacing_variant_still_clusters(self):
        # "لپ تاپ" (space) and "لپ‌تاپ" (half-space) are the same word.
        clusters = cluster_keywords(
            ["خرید لپ تاپ ارزان", "لپ‌تاپ گیمینگ"], threshold=0.30
        )
        self.assertEqual(len(clusters), 1)

    def test_unrelated_keywords_stay_apart(self):
        clusters = cluster_keywords(
            ["خرید کفش ورزشی", "آموزش زبان آلمانی"], threshold=0.30
        )
        self.assertEqual(len(clusters), 2)

    def test_generic_intent_words_do_not_glue_clusters(self):
        # Shared "خرید" alone must not merge shoes with books.
        clusters = cluster_keywords(
            ["خرید کفش ورزشی", "خرید کتاب"], threshold=0.30
        )
        self.assertEqual(len(clusters), 2)


class TestCli(unittest.TestCase):
    def test_cli_cluster_on_sample(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "pkt.py"), "cluster", str(SAMPLE)],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        clusters = json.loads(proc.stdout)
        self.assertEqual(len(clusters), 4)
        self.assertEqual(sum(c["size"] for c in clusters), 21)

    def test_cli_dedupe_on_sample(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "pkt.py"), "dedupe", str(SAMPLE)],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        # header + 19 unique keywords (21 - 2 duplicate spellings)
        self.assertEqual(len(lines), 20)
        self.assertIn("2 duplicate spellings removed", proc.stderr)


if __name__ == "__main__":
    unittest.main()
