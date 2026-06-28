"""Embed corpus_docs into a FAISS index (arc #4, phase 3).

Builds the retrieval substrate the antibody ORACLE queries for EOs / FAR clauses /
GAO fraud cases -- a SECOND index alongside the curated legal_corpus (Jay's call:
two indexes, merged by score at query time, so the curated set stays distinct).

Follows the EXACT manifest contract already on disk (legal_corpus / principalities):
  embedder text-embedding-nomic-embed-text-v1.5, 768-dim, cosine via L2-normalized
  IndexFlatIP, doc_prefix "search_document: ", query_prefix "search_query: ".
Never mix embedders in one index.

Writes:  G:\\AI-Models\\indexes\\corpus_docs.faiss + corpus_docs_meta.jsonl,
         adds a "corpus_docs" entry to index_manifest.json,
         flips corpus_docs.embedded = 1 for every embedded row.

Usage (repo root, venv python):
    python -m observatory.embed_corpus            # embed all rows with text
    python -m observatory.embed_corpus --limit 20 # small verification build
"""

from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path

import faiss
import numpy as np
import requests

from . import db

EMBED_URL = "http://localhost:1234/v1/embeddings"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
EMBED_DIMS = 768
DOC_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
BATCH_SIZE = 32
MAX_RETRIES = 5
MAX_CHARS = 6000  # nomic context is ~2k tokens; cap long clauses before embedding
MAX_META_CHARS = 1500  # clause_text stored inline in meta for the antibody oracle (retrieve wide, feed thin)

INDEX_DIR = Path(r"G:\AI-Models\indexes")
NAME = "corpus_docs"


def embed_batch(texts: list[str]) -> np.ndarray:
    payload = {"model": EMBED_MODEL, "input": texts}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(EMBED_URL, json=payload, timeout=300)
            r.raise_for_status()
            data = r.json()["data"]
            data.sort(key=lambda d: d["index"])
            return np.array([d["embedding"] for d in data], dtype=np.float32)
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            wait = 2 ** attempt
            print(f"    embed batch failed ({attempt}/{MAX_RETRIES}): {e} -- retry {wait}s")
            time.sleep(wait)


def load_rows(limit: int | None = None) -> list[dict]:
    """corpus_docs rows that have text, as embeddable records."""
    sql = ("SELECT doc_id, source, collection, citation, title, url, published, text "
           "FROM corpus_docs WHERE text IS NOT NULL AND text != '' ORDER BY doc_id")
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = []
    with db.session() as conn:
        for r in conn.execute(sql).fetchall():
            body = (r["text"] or "")[:MAX_CHARS]
            embed_text = f"{r['citation']} {r['title'] or ''}. {body}"
            rows.append({
                "doc_id": r["doc_id"],
                "source": r["source"],
                "collection": r["collection"],
                "citation": r["citation"],
                "title": r["title"],
                "url": r["url"],
                "published": r["published"],
                # Self-contained clause body in the meta sidecar (mirrors legal_corpus)
                # so the antibody oracle reads it straight from the index, no DB coupling.
                # Embed on the full body (above); store a lean copy for the drafter feed.
                "clause_text": embed_text[:MAX_META_CHARS],
                "embed_text": embed_text,
            })
    return rows


def build(limit: int | None = None) -> dict:
    rows = load_rows(limit)
    if not rows:
        print("[!] no corpus_docs rows with text -- run the fill first.")
        return {"embedded": 0}
    print(f"[*] embedding {len(rows)} corpus_docs via {EMBED_MODEL} ...")

    vectors = []
    for b in range(0, len(rows), BATCH_SIZE):
        chunk = rows[b:b + BATCH_SIZE]
        vectors.append(embed_batch([DOC_PREFIX + r["embed_text"] for r in chunk]))
        print(f"    {min(b + BATCH_SIZE, len(rows))}/{len(rows)}")
    mat = np.vstack(vectors)
    assert mat.shape == (len(rows), EMBED_DIMS), mat.shape

    faiss.normalize_L2(mat)
    index = faiss.IndexFlatIP(EMBED_DIMS)
    index.add(mat)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / f"{NAME}.faiss"))
    with open(INDEX_DIR / f"{NAME}_meta.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            meta = {k: v for k, v in r.items() if k != "embed_text"}
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    manifest_path = INDEX_DIR / "index_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest[NAME] = {
        "embedder": EMBED_MODEL,
        "embedder_serving": "LM Studio /v1/embeddings (localhost:1234)",
        "dimensions": EMBED_DIMS,
        "metric": "cosine (L2-normalized IndexFlatIP)",
        "doc_prefix": DOC_PREFIX,
        "query_prefix": QUERY_PREFIX,
        "record_count": len(rows),
        "source": "primordial-galaxy/data/primordial.db corpus_docs (eo+far+gao)",
        "index_file": f"{NAME}.faiss",
        "metadata_sidecar": f"{NAME}_meta.jsonl",
        "built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    ids = [r["doc_id"] for r in rows]
    with db.session() as conn:
        conn.executemany("UPDATE corpus_docs SET embedded = 1 WHERE doc_id = ?",
                         [(i,) for i in ids])
        conn.commit()

    print(f"[*] wrote {index.ntotal} vectors -> {INDEX_DIR / (NAME + '.faiss')}; embedded=1 flipped for {len(ids)} rows")
    return {"embedded": len(ids)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Embed corpus_docs into a FAISS index (arc #4 phase 3).")
    ap.add_argument("--limit", type=int, default=None, help="cap rows (small verification build)")
    args = ap.parse_args()
    build(args.limit)


if __name__ == "__main__":
    main()
