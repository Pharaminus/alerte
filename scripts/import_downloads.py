"""Import documents downloaded by hand into the knowledge base.

Scans the Downloads folder for recent PDFs, recognises each document from its first pages
(law number and keywords, English, French or Arabic), copies it to knowledge/docs/<country>/<ID>.pdf
and prints what was recognised. Nothing is renamed or deleted in the Downloads folder.

Usage:  .venv/bin/python scripts/import_downloads.py            # last 7 days
        .venv/bin/python scripts/import_downloads.py --days 30
        .venv/bin/python scripts/import_downloads.py --dir ..   # files saved in the project folder
"""
from __future__ import annotations

import argparse
import re
import shutil
import time
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "knowledge" / "docs"
DOWNLOADS = [Path.home() / "Téléchargements", Path.home() / "Downloads"]

# ID -> (title patterns, body patterns). Title patterns must ALL match in the first 400 characters
# of page 1 (the title block), so that laws merely cited in a preamble do not match. Body patterns
# must ALL match in the first 3 pages.
LAW = r"(?:No\.?\s*)?\(?\s*{n}\s*\)?\s*of\s*{y}|رقم\s*\(?\s*{n}\s*\)?\s*لسنة\s*{y}"
SIGNATURES = {
    "AE-05": ([LAW.format(n=3, y=2003), r"(telecommunication|الاتصالات)"], []),
    "AE-07": ([LAW.format(n=2, y=2011), r"(emergenc|الطوارئ)"], []),
    "AE-08": ([LAW.format(n=35, y=2024), r"(civil defen|الدفاع المدني)"], []),
    "AE-01": ([LAW.format(n=45, y=2021), r"(personal data|البيانات الشخصية)"], []),
    "AE-09": ([LAW.format(n=44, y=2021), r"(data office|مكتب الإمارات للبيانات)"], []),
    "AE-12": ([LAW.format(n=55, y=2023), r"(media|الإعلام)"], []),
    "AE-13": ([LAW.format(n=5, y=2024), r"(rumou?r|cybercrime|الشائعات)"], []),
    "AE-06": ([LAW.format(n=34, y=2021), r"(rumou?r|cybercrime|الشائعات)"], []),
    "AE-04": ([r"(early warning|UAE.?Alert|الإنذار المبكر)"], [r"(NCEMA|الهيئة الوطنية لإدارة الطوارئ)", r"(mobile|phone|الهاتف)"]),
    "AE-14": ([r"NCEMA\s*7000|AE/SCNS/NCEMA"], []),
    "AE-15": ([r"(National Cent(er|re) of Meteorology|NCM)"], [r"(April 2024|rainfall|precipitation)"]),
    "CM-06": ([r"d[ée]cret\s*n?°?\s*96\s*/\s*054"], []),
    "CM-19": ([r"strat[ée]gie nationale", r"intelligence artificielle"], []),
    "CM-20": ([r"cahier des charges"], [r"(licence|autorisation|concession)", r"(Agence de R[ée]gulation des T[ée]l[ée]communications|\bART\b)"]),
    "GL-10": ([r"early warnings for all"], [r"(action plan|plan d'action)"]),
    "GL-11": ([r"national emergency\s+telecommunication plans?"], []),
}


def first_pages_text(pdf: Path, n: int = 3) -> tuple[str, str]:
    """Return (title block, first n pages), whitespace collapsed."""
    try:
        with pymupdf.open(pdf) as doc:
            pages = [" ".join(doc[i].get_text().split()) for i in range(min(n, len(doc)))]
    except Exception:
        return "", ""
    return (pages[0][:400] if pages else ""), " ".join(pages)


OWN_FILES = re.compile(r"ALERTE\s*[—–-]|Plan de mise en œuvre|AI for Good Sandbox Hackathon", re.I)


def recognise(title: str, text: str) -> str | None:
    if OWN_FILES.search(text):  # our own project documents
        return None
    for doc_id, (in_title, in_body) in SIGNATURES.items():
        if all(re.search(p, title, re.I) for p in in_title) and all(re.search(p, text, re.I) for p in in_body):
            return doc_id
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--dir", action="append", help="folder to scan instead of Downloads (repeatable)")
    a = ap.parse_args()
    since = time.time() - a.days * 86400
    folders = [Path(d).expanduser() for d in a.dir] if a.dir else DOWNLOADS
    pdfs = [p for d in folders if d.exists() for p in d.glob("*.pdf") if p.stat().st_mtime >= since]
    if not pdfs:
        print("Aucun PDF récent trouvé dans le dossier Téléchargements.")
        return
    imported = skipped = 0
    for pdf in sorted(pdfs, key=lambda p: p.stat().st_mtime):
        title, text = first_pages_text(pdf)
        doc_id = recognise(title, text) if text.strip() else None
        if doc_id is None:
            skipped += 1          # unrelated or unreadable file: not listed, to respect privacy
            continue
        target = DOCS / doc_id[:2] / f"{doc_id}.pdf"
        if target.exists():
            print(f"=  {doc_id} déjà présent ({pdf.name}), ignoré")
            continue
        shutil.copy2(pdf, target)
        imported += 1
        print(f"OK {pdf.name} -> {target.relative_to(ROOT)}")
    print(f"{imported} document(s) importé(s) ; {skipped} autre(s) PDF ignoré(s) (non reconnus ou sans texte).")

if __name__ == "__main__":
    main()
