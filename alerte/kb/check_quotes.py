"""Deterministic check: every quote in mandates.csv and precedents.csv must appear word for word
in the chunk it cites (after normalising whitespace). Exit code 1 if any quote fails.

Also checks that each gap in the precedents table has examples from at least two jurisdictions.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"


def norm(s: str) -> str:
    """Collapse whitespace and unify typographic apostrophes/quotes (OCR and PDFs mix them)."""
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    chunks = {}
    for line in open(KNOW / "chunks.jsonl", encoding="utf-8"):
        c = json.loads(line)
        chunks[c["chunk_id"]] = norm(c["text"])
    failures = 0
    for table in ("mandates.csv", "precedents.csv"):
        rows = list(csv.DictReader(open(KNOW / table, encoding="utf-8")))
        ok = 0
        for r in rows:
            if not r.get("quote"):
                continue
            text = chunks.get(r["chunk_id"])
            if text is None:
                print(f"FAIL {table} {r['id']}: chunk {r['chunk_id']} not found")
                failures += 1
            elif norm(r["quote"]) not in text:
                print(f"FAIL {table} {r['id']}: quote not found in {r['chunk_id']}")
                failures += 1
            else:
                ok += 1
        print(f"{table}: {ok} quotes verified, {len(rows)} rows")
    juris = defaultdict(set)
    for r in csv.DictReader(open(KNOW / "precedents.csv", encoding="utf-8")):
        juris[r["gap"]].add(r["jurisdiction"].split(" (")[0])
    for gap in sorted(juris):
        flag = "ok" if len(juris[gap]) >= 2 else "FEWER THAN 2 JURISDICTIONS"
        print(f"  {gap}: {len(juris[gap])} jurisdictions ({', '.join(sorted(juris[gap]))}) {flag}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
