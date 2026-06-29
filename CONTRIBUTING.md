# Contributing to GovTech Hunter — Primordial Galaxy

Thanks for your interest. This project is **source-available**, not open-contribution in the
traditional sense — please read this before opening a pull request.

## License & scope

The code is published under the **[PolyForm Shield License 1.0.0](LICENSE)**. You may read, run,
modify, and self-host it for any purpose **except** building a product that competes with it. The
public repository ships a **sample corpus only**; the full curated legal corpus, validated antibody
clause library, and fraud-pattern linkage are a private, commercial layer and are not part of this
repository.

Because of the source-available license and the private data layer, this is a **founder-led**
project rather than a community-governed one. That shapes what contributions fit:

**Welcome**
- Bug reports with a clear repro (open an issue first).
- Small, focused fixes: typos, docs, obvious bugs, dependency hygiene.
- Portability and packaging improvements.

**Discuss before building**
- New features, pipeline stages, or corpus/retrieval changes — open an issue and agree on scope
  first. Unsolicited large PRs are likely to be declined regardless of quality.

**Out of scope**
- Anything that depends on or attempts to reconstruct the private corpus/clause library.

## Ground rules

1. **Open an issue first** for anything beyond a trivial fix.
2. **Keep PRs small and single-purpose.** One concern per PR.
3. **Don't add secrets or PII.** No API keys, credentials, internal hostnames/IPs, or third-party
   personal data — in code, fixtures, or commit messages. `.env` is git-ignored; keep it that way.
4. **Sign off your commits (DCO).** Add `Signed-off-by: Your Name <you@example.com>` to each commit
   (`git commit -s`). This certifies you have the right to submit the work under the project license.
5. **Match the surrounding style.** Read nearby code before writing; mirror its conventions.

## Development

- Python 3.12. Create a virtualenv and install requirements (see `README.md`).
- The stack is designed to run **sovereign-local** (no required outbound calls for core inference).
- Run the existing checks/tests before opening a PR and note in the PR what you ran.

## Conduct

All participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful.

## Contact

Questions, security reports, or licensing/commercial inquiries: **jay@apexronin.com**.
Please report suspected vulnerabilities privately by email rather than in a public issue.
