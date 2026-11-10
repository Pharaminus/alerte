"""Step 1.12 - Index the chunks and search them.

Hybrid search: multilingual embeddings (fastembed, ONNX, no PyTorch) + keyword search (BM25),
merged by reciprocal rank fusion. Keyword search catches article numbers and institution names
that embeddings miss.

Filters let each caller see only what it is entitled to:
- an institution agent: its own country and the documents of its mandate (doc_ids);
- the Legal Adviser and the gap module: also the foreign precedents (role="precedent")
  and international standards (role="international").

Build:  python -m alerte.kb.index build
Query:  python -m alerte.kb.index search "obligation des opérateurs alerte" --country CM
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[2]
KNOW = ROOT / "knowledge"
IDX = KNOW / "index"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CONTEXT_ONLY = {"context"}  # never usable as a legal basis


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9؀-ۿ]{2,}", fold(s))


def load_chunks() -> list[dict]:
    return [json.loads(l) for l in open(KNOW / "chunks.jsonl", encoding="utf-8")]


def embed_texts(texts: list[str]) -> np.ndarray:
    from fastembed import TextEmbedding
    model = TextEmbedding(MODEL, cache_dir=str(IDX / "models"))
    vecs = np.array(list(model.embed(texts, batch_size=32)), dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def build() -> None:
    IDX.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    texts = [f"{c['title']} | {c['article'] or ''}\n{c['text']}" for c in chunks]
    np.save(IDX / "embeddings.npy", embed_texts(texts))
    with open(IDX / "ids.json", "w", encoding="utf-8") as f:
        json.dump([c["chunk_id"] for c in chunks], f)
    print(f"indexed {len(chunks)} chunks")


@lru_cache(maxsize=1)
def _state():
    chunks = load_chunks()
    ids = json.load(open(IDX / "ids.json", encoding="utf-8"))
    assert ids == [c["chunk_id"] for c in chunks], "index out of date: run `python -m alerte.kb.index build`"
    emb = np.load(IDX / "embeddings.npy")
    bm25 = BM25Okapi([tokens(f"{c['title']} article {c['article'] or ''} {c['text']}") for c in chunks])
    return chunks, emb, bm25


def search(query: str, k: int = 8, country: str | None = None, doc_ids: list[str] | None = None,
           roles: list[str] | None = None, allow_context: bool = False) -> list[dict]:
    chunks, emb, bm25 = _state()
    keep = np.array([
        (country is None or c["country"] == country)
        and (doc_ids is None or c["doc_id"] in doc_ids)
        and (roles is None or c["role"] in roles)
        and (allow_context or c["role"] not in CONTEXT_ONLY)
        for c in chunks])
    if not keep.any():
        return []
    q = embed_texts([query])[0]
    dense = emb @ q
    sparse = bm25.get_scores(tokens(query))
    dense[~keep] = -np.inf
    sparse[~keep] = -np.inf
    rank_d = {i: r for r, i in enumerate(np.argsort(-dense)[:200]) if keep[i]}
    rank_s = {i: r for r, i in enumerate(np.argsort(-sparse)[:200]) if keep[i] and sparse[i] > 0}
    fused = {i: 1 / (60 + rank_d.get(i, 1000)) + 1 / (60 + rank_s.get(i, 1000)) for i in set(rank_d) | set(rank_s)}
    best = sorted(fused, key=fused.get, reverse=True)[:k]
    return [{**chunks[i], "score": round(fused[i], 5)} for i in best]


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--country")
    s.add_argument("--roles", nargs="*")
    s.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        for r in search(a.query, k=a.k, country=a.country, roles=a.roles):
            print(f"{r['chunk_id']:22s} {r['score']:.4f}  {r['text'][:110].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
