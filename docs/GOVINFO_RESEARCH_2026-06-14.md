# govinfo.gov as a Data Source — Research Brief (2026-06-14)

**Arc item #3.** Scope govinfo.gov (and adjacent primary-source APIs) as the feed
for the `corpus_docs` knowledge store that the antibody ORACLE agent (arc #4)
will draw on: FAR/DFARS clauses, statutes, Executive Orders, OMB memos, and past
procurement-fraud cases. Sovereign-local: we pull from public APIs and store
locally in `data/primordial.db`; no cloud dependency.

All endpoints below were probed live on 2026-06-14 with `DEMO_KEY`.

---

## 1. The govinfo API

- **Base URL:** `https://api.govinfo.gov`
- **Auth:** api.data.gov key via `?api_key=...`. `DEMO_KEY` works for testing but
  is heavily rate-limited. Real key: https://www.govinfo.gov/api-signup
  → set `GOVINFO_API_KEY` in `.env` (the ingest reads it, falls back to DEMO_KEY).
- **Rate limits (real key):** 36,000/hour, 1,200/min, 40/sec. Headers
  `X-RateLimit-Limit` / `X-RateLimit-Remaining`.
- **Formats per package/granule:** `htm`, `xml`, `pdf`, `mods` (metadata),
  `premis`, `zip`.

### Endpoints that matter for us
| Endpoint | Use |
|----------|-----|
| `GET /collections` | list collection codes (confirmed live) |
| `GET /collections/{code}/{lastModifiedStart}[/{end}]` | enumerate a collection by **lastModified** (this is the one that returns the GAO archive) |
| `GET /published/{dateStart}/{dateEnd}?collection={code}` | enumerate by **dateIssued** (good for FR/CFR/BILLS; returns 0 for GAO — see below) |
| `POST /search` | full-text search across collections |
| `GET /packages/{packageId}/summary` | package metadata + download links |
| `GET /packages/{packageId}/{htm\|xml\|pdf}` | **full text** of a package |
| `GET /packages/{packageId}/granules` | list granules (e.g. individual FAR sections in a CFR volume) |
| `GET /packages/{packageId}/granules/{granuleId}/{htm\|xml}` | full text of one clause/section |

**Package vs granule:** a package is a whole publication (a CFR Title 48 volume,
one daily Federal Register issue). A granule is a subdivision — an individual FAR
section, one FR document. FAR/DFARS clause-level text = CFR granules.

---

## 2. Source routing (decisions)

The right source depends on the document class. Not everything belongs in govinfo.

### Executive Orders → **Federal Register API** (not govinfo)
- `https://www.federalregister.gov/api/v1/documents.json`
  with `conditions[presidential_document_type]=executive_order`.
- **No API key. Structured EO fields** (`executive_order_number`, `signing_date`,
  `title`, `html_url`, `abstract`). Live probe: **1,547 EOs, current to EO 14411
  (2026-06-03)**.
- govinfo's EO codification lives in CFR **Title 3** (annual edition) and lags
  ~1 year — unusable for "newest EOs." **Decision: EOs come from Federal Register.**
- Implemented: `observatory.ingest eo --limit N` → 24 EOs seeded.

### FAR / DFARS clauses → **govinfo CFR, Title 48**
- FAR = Title 48 **Chapter 1**; DFARS = Title 48 **Chapter 2**; other agency
  supplements are further chapters.
- Package IDs look like `CFR-2025-title48-vol1` … `vol9`; clause granules like
  `CFR-2016-title48-vol2-sec52-204-21` (live-confirmed format).
- **Caveat — annual edition lag:** CFR annual editions publish months into the
  year, so the renumbered clauses we track (FAR 52.240-93, DFARS 252.240-7997,
  from the Feb 2026 RFO) may not appear in a CFR annual edition yet. For the
  bleeding edge, the renumbering itself was published in the **Federal Register**
  (FR collection) — pull the RFO final rule from FR, fall back to CFR annual for
  stable clause text. (See STATE.md reg ground-truth lines.)
- **Not yet implemented** in `ingest.py` — granule enumeration of Title 48 is the
  next ingest to write (scaffold + routing notes are in the module docstring).

### Past procurement-fraud cases → **govinfo GAOREPORTS** (historical) + gao.gov (current)
- **Finding:** `GAOREPORTS` is a **historical archive** — 16,569 packages but the
  newest `dateIssued` is ~2000. `published/{dateIssued}` for recent years returns
  **0**. The **collections service** (lastModified) is what returns them; many are
  directly on point ("Federal Acquisition: Trends, Reforms, and Challenges",
  Comptroller General bid-protest decisions).
- **Decision:** ingest the historical archive via the collections service for the
  oracle's fraud-pattern grounding; for **current** GAO reports/decisions, wire
  gao.gov directly later (separate path, not in govinfo).
- Implemented: `observatory.ingest gao --start YYYY-MM-DD` → 50 reports seeded.

### OMB memos (e.g. M-26-04) → **whitehouse.gov/omb** (neither govinfo nor FR)
- OMB memoranda are **not** in govinfo or the Federal Register. They live at
  whitehouse.gov/omb as standalone PDFs. Separate scraper path — flagged, not built.

### Also available if needed
- `USCODE` (statutes), `PLAW` (public laws), `BILLS`/`BILLSTATUS`, `CREC`,
  `CPD` (Compilation of Presidential Documents — proclamations, memoranda).

---

## 3. How it plugs into the spine

Everything lands in `corpus_docs` (see `observatory/db.py`):
`source` (eo|far|dfars|gao|omb|...), `collection`, `citation` (unique per source),
`title`, `url` (primary source), `published`, `text`, `embedded` flag, `meta_json`.

Dedup key is `(source, citation)` so re-runs update in place. `text` is stored
empty for list-level pulls and filled on demand (the `/packages/.../htm` or
granule fetch) — keeps the seed cheap, defers heavy full-text pulls to when the
oracle actually needs a document.

**Current state:** 74 docs seeded (24 EO, 50 GAO), `embedded=0`.

---

## 4. Next steps (sets up arc #4 — antibody ORACLE)

1. **Title 48 granule ingest** — enumerate FAR (ch.1) + DFARS (ch.2) clause
   granules, store full `htm` text. Source-route renumbered clauses to FR.
2. **Full-text fill** — for seeded EO/GAO rows, pull `/packages/.../htm` text on
   demand (or batch) so retrieval has real content, not just titles.
3. **Embed into FAISS** — run the seeded corpus_docs through nomic-embed (LM Studio)
   into a new index under `G:\AI-Models\indexes`, mirroring the legal_corpus /
   principalities pattern; flip `embedded=1`. This is the retrieval substrate the
   antibody ORACLE queries.
4. **OMB + current-GAO scrapers** — whitehouse.gov/omb and gao.gov paths.
5. **Get a real `GOVINFO_API_KEY`** into `.env` before any bulk sweep (DEMO_KEY
   will rate-limit a Title 48 granule walk).

---

## Sources
- [govinfo API repo (USGPO)](https://github.com/usgpo/api)
- [govinfo API signup](https://www.govinfo.gov/api-signup)
- [govinfo CFR collection](https://www.govinfo.gov/app/collection/cfr)
- [Federal Register API v1](https://www.federalregister.gov/developers/documentation/api/v1)
- Live probes 2026-06-14: `/collections`, `/collections/GAOREPORTS/...`,
  `/published/.../FR`, federalregister.gov EO query (DEMO_KEY / no-key).
