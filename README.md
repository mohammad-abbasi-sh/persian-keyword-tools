# persian-keyword-tools

[🇮🇷 توضیحات فارسی](README-fa.md)

**Normalize, dedupe and cluster Persian keywords — the cleanup step every Persian SEO keyword list needs before it can be trusted.**

```bash
python pkt.py normalize examples/sample-keywords.csv
python pkt.py dedupe examples/sample-keywords.csv -o deduped.csv
python pkt.py cluster examples/sample-keywords.csv -o clusters.json
```

No API key, no network. The core is pure Python standard library; [Hazm](https://github.com/roshan-research/hazm) is an optional extra for stronger stemming.

## The problem

A Persian keyword list exported from Search Console or a planner is never clean:

| Mess | Example | What happens without cleanup |
| --- | --- | --- |
| Arabic letters mixed in | `خريد كتاب` vs `خرید کتاب` | The same query counts twice |
| Missing half-space (نیم‌فاصله) | `کتاب ها`, `می روم` | Variants never match each other |
| Diacritics / tatweel pasted in | `مُدرسه`, `کتـــاب` | Phantom keywords in reports |
| Arabic-Indic digits | `قیمت ١٢٣` | Splits volume by spelling |
| Same topic, ten spellings | `لپ تاپ` / `لپ‌تاپ` / `لپتاپ` | No clustering, no topic view |

This tool fixes all five, then groups what's left into topics.

## What it does

- **`normalize`** — Arabic ي/ك → Persian ی/ک, half-space repair (`می روم` → `می‌روم`, `کتاب ها` → `کتاب‌ها`), diacritic/tatweel removal, Arabic-Indic → Persian digits, whitespace collapse.
- **`stem`** — a conservative rule-based stemmer (plurals, comparatives, verb prefixes) plus Hazm's stemmer when installed. It deliberately never strips verb endings (`خرید` stays `خرید`, never `خر`) and never mangles nouns (`رمان` is not `رم` + `ان`).
- **`dedupe`** — collapses spelling variants to one canonical keyword.
- **`cluster`** — greedy agglomerative clustering on stemmed token overlap (Jaccard + overlap on adjacent-token pairs, so `لپ تاپ` still matches `لپ‌تاپ`). Generic intent words (`خرید`، `قیمت`، `بهترین`) are ignored for similarity, so they can't glue unrelated topics together.

## Real run on the sample list

`examples/sample-keywords.csv` is 21 authored sample keywords in 4 topics (shoes, German learning, laptops, books) with intentional spelling mess. Actual output:

```bash
$ python pkt.py dedupe examples/sample-keywords.csv
# 21 keywords -> 19 unique (2 duplicate spellings removed)

$ python pkt.py cluster examples/sample-keywords.csv
# 21 keywords -> 4 clusters (threshold 0.3)
```

| Cluster | Size | Keywords |
| --- | --- | --- |
| خرید کتاب | 6 | خرید کتاب، کتاب‌های خوب، کتاب رمان خوب، بهترین کتاب رمان |
| خرید کفش ورزشی | 5 | خرید کفش ورزشی، کفش ورزشی ارزان، خرید کفش دویدن، کفش دویدن مردانه، بهترین کفش دویدن |
| دوره زبان آلمانی | 5 | دوره زبان آلمانی، آموزش زبان آلمانی، یادگیری زبان آلمانی، آموزش آلمانی مبتدی، کلاس زبان آلمانی آنلاین |
| لپ‌تاپ گیمینگ | 5 | لپ‌تاپ گیمینگ، قیمت لپتاپ گیمینگ، خرید لپ تاپ ارزان، خرید لپ‌تاپ دانشجویی، بهترین لپ‌تاپ دانشجویی |

Full outputs: [`examples/sample-normalized.csv`](examples/sample-normalized.csv), [`examples/sample-clusters.json`](examples/sample-clusters.json).

## Usage

Input is a CSV with a `keyword` column (or the first column), a `.txt` file with one keyword per line, or `-` for stdin.

```bash
# Normalize + stem a list (CSV out: keyword, normalized, stemmed)
python pkt.py normalize keywords.csv -o normalized.csv

# Collapse duplicate spellings (CSV out: keyword, normalized, variants)
python pkt.py dedupe keywords.csv -o deduped.csv

# Cluster into topics (JSON out; --format csv for CSV)
python pkt.py cluster keywords.csv -o clusters.json --threshold 0.30
```

Use it as a library too:

```python
from persian_keyword_tools import normalize, stem, cluster_keywords

normalize("خريد كتاب هاي خوب")   # 'خرید کتاب‌های خوب'
stem("کتاب‌ها")                   # 'کتاب'
cluster_keywords(["خرید کفش ورزشی", "کفش ورزشی ارزان"], threshold=0.30)
```

## Tests

19 unit tests + 9 doctests, passing both with Hazm installed and on pure stdlib:

```bash
python -m unittest discover -s tests -v
python -m pytest --doctest-modules persian_keyword_tools/ -q
```

## Why I built this

I'm an SEO manager working in Persian every day. English keyword tools treat Persian as an afterthought — they don't know what a half-space is, and they split one topic into ten spellings. This is the cleanup layer I run before any keyword mapping or content plan. Part of my [12 projects in 12 weeks](https://github.com/mohammad-abbasi-sh) series: SEO × AI, built in public.

MIT — see [LICENSE](LICENSE).
