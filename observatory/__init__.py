"""Observatory — local observability layer for the GovTech Hunter pipeline.

Sovereign-local, zero-cloud. A SQLite spine (`data/primordial.db`) records every
scanner run and every opportunity, plus a `corpus_docs` knowledge store for the
govinfo / FAR / DFARS / EO ingest that the ORACLE agents draw on.

This package is the foundation for three arc items:
  #1 observability UI  -> observatory.server (FastAPI live dashboard)
  #2 the database      -> observatory.db (the spine)
  #3 govinfo ingest    -> corpus_docs table + observatory.db.upsert_corpus_doc

Hard rule: nothing in here may break the scan pipeline. The recorder hook in
main.py is wrapped so any failure here is logged and swallowed — observability
is never allowed to take down acquisition.
"""

from .db import DB_PATH, connect, init_db

__all__ = ["DB_PATH", "connect", "init_db"]
