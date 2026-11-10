"""Step 1.11 - Cut every extracted text article by article (laws) or section by section (other documents).

Output: knowledge/chunks.jsonl, one JSON object per chunk, and knowledge/text/_chunk_report.csv.

Article headings are recognised with a pattern chosen per document style. To avoid false
positives (cross-references, numbered lists), a heading is only accepted when its number
follows the previous accepted one (n+1 ... n+5): article numbering must progress.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
TEXT = KNOW / "text"
MAX_WORDS = 450        # longer articles are split by paragraph, keeping the article number
SECTION_WORDS = 380    # target size for documents without articles

NUM = r"(\d+|1er|premier)"
STYLES = {
    # French laws and decrees: "Article 20.-", "ARTICLE 1er.-", "Article premier", "Art. 5"
    "fr_article": re.compile(rf"^[ \t]*(?:ARTICLE|Article|Art\.)[\s.]*{NUM}(?:\s*(?:er|bis|ter))?\b", re.M),
    # UAE English translations: "Article (1)"
    "paren_article": re.compile(r"^[ \t]*Article\s*\(\s*(\d+)\s*\)", re.M),
    # EU acts: a line that contains only "Article 110"
    "eu_article": re.compile(r"^[ \t]*Article\s+(\d+)[a-z]?\s*$", re.M),
    # US Code of Federal Regulations: "§ 10.400"
    "cfr_section": re.compile(r"^[ \t]*§\s*10\.(\d+)", re.M),
    # Philippine acts: "Section 4."
    "ph_section": re.compile(r"^[ \t]*(?:SECTION|Section|SEC\.|Sec\.)\s*(\d+)\.", re.M),
    # South African acts: "7. (1) The national..." or "15. Disaster..."
    "za_section": re.compile(r"^[ \t]*(\d{1,3})[A-Z]?\.\s*(?:\(\s*1\s*\)\s*)?[A-Z(]", re.M),
    # English sections of bilingual gazettes: "Section 1.—", "Section 2 (1) :"
    "en_section": re.compile(r"^[ \t]*Section\s+(\d+)\s*[.(:—–-]", re.M),
    # Arabic: "المادة (12)"
    "ar_article": re.compile(r"^المادة\s*\(?\s*(\d+)", re.M),
}
DOC_STYLE = {
    "AE-06": "paren_article", "AE-01": "paren_article", "AE-05": "paren_article",
    "AE-09": "paren_article", "AE-12": "paren_article",
    "GL-01": "eu_article", "GL-02": "eu_article", "GL-03": "eu_article",
    "CM-09": "en_section",
    "GL-04": "ph_section", "GL-05": "cfr_section", "GL-19": "za_section",
}
# Documents holding several texts (e.g. a gazette issue): keep only the part between two markers.
DOC_WINDOW = {
    "CM-09": (r"Law No\. 90-47 of 19 December 1990\s*\n\s*relating", r"Section 11\.[^\n]*\n(?:.*\n){0,6}?.*Paul Biya"),
}
FRENCH_LEGAL = {"CM-01", "CM-02", "CM-03", "CM-04", "CM-05", "CM-07", "CM-08", "CM-09", "CM-11"}


def as_int(token: str) -> int:
    return 1 if token.lower() in ("1er", "premier") else int(token)


def page_at(text: str, pos: int) -> int:
    marks = [(m.start(), int(m.group(1))) for m in re.finditer(r"\[\[page (\d+)\]\]", text)]
    page = 1
    for start, n in marks:
        if start <= pos:
            page = n
    return page


def strip_marks(s: str) -> str:
    return re.sub(r"\[\[page \d+\]\]\n?", "", s).strip()


def split_long(text: str, limit: int) -> list[str]:
    words = text.split()
    if len(words) <= limit:
        return [text]
    parts, cur = [], []
    for para in re.split(r"\n(?=\s*(?:\(\d+\)|\d+\.|[a-z]\)|–|-|•))|\n\n", text):
        if cur and len(" ".join(cur).split()) + len(para.split()) > limit:
            parts.append("\n".join(cur))
            cur = []
        cur.append(para)
    if cur:
        parts.append("\n".join(cur))
    # hard split anything still too long
    out = []
    for p in parts:
        w = p.split()
        out += [" ".join(w[i:i + limit]) for i in range(0, len(w), limit)] if len(w) > limit * 1.5 else [p]
    return out


ANNEX = re.compile(r"^[ \t]*(?:ANNEX(?:ES)?|ANNEXE|Annex)\s*(?:[IVX]+|\d+)?\s*$", re.M)


def article_chunks(doc_id: str, text: str, pattern: re.Pattern) -> list[dict]:
    heads, last = [], 0
    annex = None
    for m in pattern.finditer(text):
        if heads:
            a = ANNEX.search(text, heads[-1][0])
            if a and a.start() < m.start():
                annex = a.start()
                break
        n = as_int(m.group(1))
        step_ok = n > last if pattern is STYLES["cfr_section"] else last < n <= last + 5
        if step_ok or (not heads and n == 1):
            heads.append((m.start(), n))
            last = n
    if len(heads) < 3:
        return []
    chunks = []
    preamble = strip_marks(text[: heads[0][0]])
    if len(preamble.split()) > 40:
        for i, part in enumerate(split_long(preamble, SECTION_WORDS), 1):
            chunks.append({"chunk_id": f"{doc_id}#preamble-{i}", "article": None, "part": i,
                           "page": page_at(text, 0), "text": part})
    for i, (start, n) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else (annex or len(text))
        body = strip_marks(text[start:end])
        for j, part in enumerate(split_long(body, MAX_WORDS), 1):
            chunks.append({"chunk_id": f"{doc_id}#art-{n}" + (f"-{j}" if j > 1 else ""), "article": str(n),
                           "part": j, "page": page_at(text, start), "text": part})
    if annex is not None:
        for c in section_chunks(doc_id, text[annex:]):
            c["chunk_id"] = c["chunk_id"].replace("#sec-", "#annex-")
            chunks.append(c)
    return chunks


def section_chunks(doc_id: str, text: str) -> list[dict]:
    chunks, buf, buf_page, k = [], [], 1, 0
    for block in re.split(r"\n\s*\n", text):
        page_m = re.search(r"\[\[page (\d+)\]\]", block)
        clean = strip_marks(block)
        if not clean:
            if page_m:
                buf_page = buf_page if buf else int(page_m.group(1))
            continue
        if not buf and page_m:
            buf_page = int(page_m.group(1))
        buf.append(clean)
        if len(" ".join(buf).split()) >= SECTION_WORDS:
            k += 1
            chunks.append({"chunk_id": f"{doc_id}#sec-{k}", "article": None, "part": 1, "page": buf_page, "text": "\n".join(buf)})
            buf = []
    if buf and len(" ".join(buf).split()) > 15:
        k += 1
        chunks.append({"chunk_id": f"{doc_id}#sec-{k}", "article": None, "part": 1, "page": buf_page, "text": "\n".join(buf)})
    return chunks


def tagger(tags: dict):
    # acronyms (all caps) must match case-sensitively to avoid "art" matching "ART"
    compiled: dict = {group: {} for group in tags}
    for group in tags:
        for name, kws in tags[group].items():
            acr = [k for k in kws if k.isupper()]
            low = [k for k in kws if not k.isupper()]
            parts = [rf"(?i:{re.escape(k)})" for k in low] + [rf"\b{re.escape(k)}\b" for k in acr]
            compiled[group][name] = re.compile("|".join(parts))
    return lambda text, group: sorted(n for n, rx in compiled[group].items() if rx.search(text))


def main() -> None:
    manifest = {r["id"]: r for r in csv.DictReader(open(KNOW / "manifest.csv", encoding="utf-8"))}
    tag = tagger(yaml.safe_load(open(KNOW / "tags.yaml", encoding="utf-8")))
    out, report = [], []
    for path in sorted(TEXT.glob("*.txt")):
        doc_id = path.stem
        meta = manifest[doc_id]
        text = path.read_text(encoding="utf-8")
        if doc_id in DOC_WINDOW:
            start_rx, end_rx = DOC_WINDOW[doc_id]
            start = re.search(start_rx, text)
            end = re.compile(end_rx).search(text, start.start()) if start else None
            if start and end:
                pages_before = re.findall(r"\[\[page \d+\]\]", text[: start.start()])
                text = (pages_before[-1] + "\n" if pages_before else "") + text[start.start(): end.end()]
        style = DOC_STYLE.get(doc_id) or ("fr_article" if doc_id in FRENCH_LEGAL else None)
        chunks = article_chunks(doc_id, text, STYLES[style]) if style else []
        method = style if chunks else "sections"
        if not chunks:
            chunks = section_chunks(doc_id, text)
        evidence = "documented" if meta["status"] == "official" else "inferred"
        for c in chunks:
            c.update({
                "doc_id": doc_id, "country": meta["country"], "doc_type": meta["doc_type"], "role": meta["role"],
                "title": meta["title"], "language": meta["language"], "url": meta["url"], "status": meta["status"],
                "text_quality": meta["text_quality"], "evidence": evidence,
                "institutions": tag(c["text"], "institutions"), "topics": tag(c["text"], "topics"),
            })
            out.append(c)
        arts = [c for c in chunks if c["article"]]
        report.append({"id": doc_id, "method": method, "chunks": len(chunks),
                       "articles": len({c["article"] for c in arts}),
                       "first_last": f"{arts[0]['article']}-{arts[-1]['article']}" if arts else ""})
    with open(KNOW / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in out:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(TEXT / "_chunk_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0]))
        w.writeheader()
        w.writerows(report)
    for r in report:
        print(f"{r['id']:7s} {r['method']:13s} {r['chunks']:4d} chunks  {r['articles']:4d} articles  {r['first_last']}")
    print("TOTAL chunks:", len(out))


if __name__ == "__main__":
    main()
