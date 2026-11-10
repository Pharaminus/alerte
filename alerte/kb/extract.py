"""Step 1.10 - Extract and clean the text of every document listed in the manifest.

Output: knowledge/text/<ID>.txt (with "[[page N]]" markers) and
knowledge/text/_extraction_report.csv (pages, characters per page, pages needing OCR).
"""
from __future__ import annotations

import csv
import html
import re
import zipfile
from collections import Counter
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
TEXT = KNOW / "text"
MIN_CHARS_PER_PAGE = 100  # below this a page is considered scanned (OCR needed)


def read_manifest() -> list[dict]:
    with open(KNOW / "manifest.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pdf_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as doc:
        return [page.get_text() for page in doc]


def html_pages(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if "charset=windows-1252" in raw.lower() or "�" in raw:
        raw = path.read_bytes().decode("cp1252", errors="ignore")
    raw = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</tr>|</div>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return ["\n".join(l.strip() for l in text.splitlines() if l.strip())]


def docx_pages(path: Path) -> list[str]:
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    lines = ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in paras]
    return ["\n".join(html.unescape(l) for l in lines if l.strip())]


def remove_repeated_lines(pages: list[str]) -> list[str]:
    """Drop headers/footers: short lines that appear on more than half of the pages."""
    if len(pages) < 4:
        return pages
    counts = Counter()
    for p in pages:
        counts.update({l.strip() for l in p.splitlines() if 0 < len(l.strip()) < 80})
    repeated = {l for l, c in counts.items() if c > len(pages) / 2 and not re.match(r"(?i)^(article|art\.|section)", l)}
    return ["\n".join(l for l in p.splitlines() if l.strip() not in repeated) for p in pages]


def clean(text: str) -> str:
    text = text.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # words cut at line end
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> None:
    TEXT.mkdir(parents=True, exist_ok=True)
    report = []
    for row in read_manifest():
        if not row["file"] or not row["file"].startswith("docs/"):
            continue
        path = KNOW / row["file"]
        if not path.exists():
            report.append({"id": row["id"], "pages": 0, "chars_per_page": 0, "low_text_pages": "", "status": "missing file"})
            continue
        suffix = path.suffix.lower()
        ocr_file = KNOW / "ocr" / f"{row['id']}.txt"
        if ocr_file.exists():  # scanned document: use the Tesseract output (alerte.kb.ocr)
            pages = ocr_file.read_text(encoding="utf-8").split("\f")
        elif suffix == ".pdf":
            pages = pdf_pages(path)
        elif suffix in (".html", ".htm"):
            pages = html_pages(path)
        else:
            pages = docx_pages(path)
        pages = [clean(p) for p in remove_repeated_lines(pages)]
        low = [str(i + 1) for i, p in enumerate(pages) if len(p) < MIN_CHARS_PER_PAGE]
        body = "\n\n".join(f"[[page {i + 1}]]\n{p}" for i, p in enumerate(pages))
        (TEXT / f"{row['id']}.txt").write_text(body, encoding="utf-8")
        cpp = sum(len(p) for p in pages) // max(len(pages), 1)
        status = "ocr_required" if len(low) > len(pages) / 2 else ("partial_ocr" if low else "ok")
        report.append({"id": row["id"], "pages": len(pages), "chars_per_page": cpp,
                       "low_text_pages": " ".join(low[:30]) + (" ..." if len(low) > 30 else ""), "status": status})
    with open(TEXT / "_extraction_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "pages", "chars_per_page", "low_text_pages", "status"])
        w.writeheader()
        w.writerows(report)
    for r in report:
        print(f"{r['id']:7s} {r['pages']:4d} p  {r['chars_per_page']:5d} car/p  {r['status']}")


if __name__ == "__main__":
    main()
