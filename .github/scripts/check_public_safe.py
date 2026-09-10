#!/usr/bin/env python3
"""Public-safe guard for primordial-galaxy's public mirror.

Fails if the checked-out tree contains any path that belongs to the
private commercial layer (Heartland/entity_procurement, the validated
antibody library, etc). Run by
.github/workflows/public-safe-guard.yml on every PR/push targeting
main, but only inside apex-ronin/primordial-galaxy (see that
workflow's `if:` condition) — the jsnnlsn-prog private mirror is
exempt and keeps carrying the full commercial layer.

This checks path existence, not diff content, so it catches a
forbidden file regardless of which commit in a PR introduced it.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Paths that must never exist in this repo's tree. Add to this list as
# more private-commercial-layer files are identified — exact repo-relative
# paths, or directory prefixes (checked with a leading-segment match).
FORBIDDEN_PATHS = [
    "observatory/entity_procurement.py",
    "scripts/set_mirror_secrets.ps1",
]

# NOTE (2026-09-07 review): Heartland code also lives inside
# observatory/server.py (the /heartland routes) and observatory/db.py (the
# entity_procurement table) — both otherwise-legitimate, presumably-public
# files. A path-existence check can't partially block a file, and
# entity_procurement.py is imported by both, so removing it alone would
# break their imports. Covering this properly needs those Heartland-specific
# pieces pulled into their own module first; until then this check does not
# catch that gap.


def is_forbidden(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    for forbidden in FORBIDDEN_PATHS:
        forbidden_parts = Path(forbidden).parts
        if parts[: len(forbidden_parts)] == forbidden_parts:
            return True
    return False


def main() -> int:
    failures = [p for p in FORBIDDEN_PATHS if (REPO_ROOT / p).exists()]

    if failures:
        print("PUBLIC-SAFE GUARD FAILED — this content cannot reach the public repo:\n")
        for f in failures:
            print(f"  - {f}")
        print(
            "\nIf this is genuinely public-safe now, remove it from "
            "FORBIDDEN_PATHS in .github/scripts/check_public_safe.py. "
            "Otherwise, keep this change on the jsnnlsn-prog private "
            "mirror only."
        )
        return 1

    print("Public-safe guard passed — no forbidden paths present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
