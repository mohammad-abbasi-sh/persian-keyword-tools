#!/usr/bin/env python3
"""pkt — Persian keyword tools CLI.

    python pkt.py normalize examples/sample-keywords.csv
    python pkt.py dedupe examples/sample-keywords.csv -o deduped.csv
    python pkt.py cluster examples/sample-keywords.csv -o clusters.json

Input is a CSV with a `keyword` column (or the first column), a .txt
file with one keyword per line, or `-` for stdin. No API key, no
network — everything runs locally.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from persian_keyword_tools import (  # noqa: E402
    cluster_keywords,
    dedupe_keywords,
    hazm_available,
    normalize,
    stem,
)


def read_keywords(path: str) -> list[str]:
    """Read keywords from a CSV, a .txt, or stdin ("-")."""
    if path == "-":
        return [line.strip() for line in sys.stdin if line.strip()]
    text = Path(path).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    if path.endswith(".csv"):
        rows = list(csv.reader(lines))
        if not rows:
            return []
        header = [h.strip().lower() for h in rows[0]]
        if "keyword" in header:
            col = header.index("keyword")
            return [row[col].strip() for row in rows[1:] if len(row) > col and row[col].strip()]
        if rows and all(h and not h[0].isdigit() for h in header):
            # First row looks like a header without a keyword column:
            # treat it as one anyway if it is not a keyword itself.
            return [row[0].strip() for row in rows[1:] if row and row[0].strip()]
        return [row[0].strip() for row in rows if row and row[0].strip()]
    return [line.strip() for line in lines]


def _write(path: str | None, content: str) -> None:
    if path:
        Path(path).write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)


def cmd_normalize(args: argparse.Namespace) -> int:
    keywords = read_keywords(args.input)
    engine = "hazm" if hazm_available() else "light"
    print(f"# stemming engine: {engine}", file=sys.stderr)
    rows = [
        {
            "keyword": kw,
            "normalized": normalize(kw),
            "stemmed": " ".join(stem(tok, engine="auto") for tok in normalize(kw).split(" ")),
        }
        for kw in keywords
    ]
    out = sys.stdout if args.output is None else open(args.output, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(out, fieldnames=["keyword", "normalized", "stemmed"])
    writer.writeheader()
    writer.writerows(rows)
    if args.output is not None:
        out.close()
    print(f"# {len(rows)} keywords normalized", file=sys.stderr)
    return 0


def cmd_dedupe(args: argparse.Namespace) -> int:
    keywords = read_keywords(args.input)
    groups = dedupe_keywords(keywords)
    dupes = sum(len(v) - 1 for v in groups.values())
    rows = [{"keyword": v[0], "normalized": k, "variants": len(v)} for k, v in groups.items()]
    out = sys.stdout if args.output is None else open(args.output, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(out, fieldnames=["keyword", "normalized", "variants"])
    writer.writeheader()
    writer.writerows(rows)
    if args.output is not None:
        out.close()
    print(
        f"# {len(keywords)} keywords -> {len(groups)} unique "
        f"({dupes} duplicate spellings removed)",
        file=sys.stderr,
    )
    return 0


def cmd_cluster(args: argparse.Namespace) -> int:
    keywords = read_keywords(args.input)
    clusters = cluster_keywords(keywords, threshold=args.threshold)
    if args.format == "csv":
        lines = ["label,size,keywords"]
        for cluster in clusters:
            joined = " | ".join(cluster["keywords"])
            lines.append(f'"{cluster["label"]}",{cluster["size"]},"{joined}"')
        _write(args.output, "\n".join(lines) + "\n")
    else:
        _write(args.output, json.dumps(clusters, ensure_ascii=False, indent=2) + "\n")
    print(
        f"# {len(keywords)} keywords -> {len(clusters)} clusters "
        f"(threshold {args.threshold})",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pkt",
        description="Normalize, dedupe and cluster Persian keywords.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_norm = sub.add_parser("normalize", help="normalize + stem a keyword list")
    p_norm.add_argument("input", help="CSV/.txt file, or - for stdin")
    p_norm.add_argument("-o", "--output", help="output CSV (default: stdout)")
    p_norm.set_defaults(func=cmd_normalize)

    p_dedupe = sub.add_parser("dedupe", help="collapse duplicate spellings")
    p_dedupe.add_argument("input", help="CSV/.txt file, or - for stdin")
    p_dedupe.add_argument("-o", "--output", help="output CSV (default: stdout)")
    p_dedupe.set_defaults(func=cmd_dedupe)

    p_cluster = sub.add_parser("cluster", help="group keywords by topic overlap")
    p_cluster.add_argument("input", help="CSV/.txt file, or - for stdin")
    p_cluster.add_argument("-o", "--output", help="output file (default: stdout)")
    p_cluster.add_argument("--threshold", type=float, default=0.30,
                           help="min Jaccard similarity to join a cluster (default 0.30)")
    p_cluster.add_argument("--format", choices=["json", "csv"], default="json")
    p_cluster.set_defaults(func=cmd_cluster)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
