"""Step 1.10 (scanned documents) - OCR with Tesseract.

Renders each page at 300 dpi and runs the `tesseract` command line. The result goes to
knowledge/ocr/<ID>.txt (pages separated by a form feed), which extract.py then uses
instead of the PDF text layer.

Usage:  python -m alerte.kb.ocr CM-01 CM-07 CM-09 GL-14
        python -m alerte.kb.ocr --all-scans     # every document whose text_quality is scan/poor
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
OCR = KNOW / "ocr"
LANG = {"fr": "fra", "en": "eng", "ar": "ara"}


def tess_langs(language_field: str) -> str:
    codes = [LANG[l.strip()] for l in language_field.split(";") if l.strip() in LANG]
    return "+".join(dict.fromkeys(codes)) or "eng"


def ocr_page(png: Path, langs: str) -> str:
    out = subprocess.run(["tesseract", str(png), "-", "-l", langs, "--psm", "3"],
                         capture_output=True, text=True, check=True)
    return out.stdout


def ocr_document(doc_id: str, pdf: Path, langs: str) -> None:
    with tempfile.TemporaryDirectory() as tmp, pymupdf.open(pdf) as doc:
        pngs = []
        for i, page in enumerate(doc):
            p = Path(tmp) / f"p{i:04d}.png"
            page.get_pixmap(dpi=300).save(p)
            pngs.append(p)
        with ThreadPoolExecutor(max_workers=4) as pool:
            pages = list(pool.map(lambda p: ocr_page(p, langs), pngs))
    OCR.mkdir(exist_ok=True)
    (OCR / f"{doc_id}.txt").write_text("\f".join(pages), encoding="utf-8")
    chars = sum(len(p.strip()) for p in pages)
    print(f"{doc_id}: {len(pages)} pages, {chars // max(len(pages), 1)} car/page, langues {langs}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--all-scans", action="store_true")
    a = ap.parse_args()
    rows = {r["id"]: r for r in csv.DictReader(open(KNOW / "manifest.csv", encoding="utf-8"))}
    ids = a.ids or [i for i, r in rows.items() if a.all_scans and r["text_quality"] in ("scan_ocr_required", "ocr", "ocr_poor") and r["file"]]
    for doc_id in ids:
        r = rows[doc_id]
        ocr_document(doc_id, KNOW / r["file"], tess_langs(r["language"]))


if __name__ == "__main__":
    main()
