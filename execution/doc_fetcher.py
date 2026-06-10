"""
Document fetcher — pulls full RFP text from posting pages (handoff Item 3.4).

CSDA (and most district) postings link the actual RFP documents from an HTML
posting page, so `link` rarely ends in .pdf and the red team / antibody chain
was running on title+snippet only. This module:

  1. Direct PDF links  → pdf_reader.get_pdf_text (cached).
  2. HTML posting pages → fetch page, extract visible text, harvest linked
     PDF documents (RFP/RFQ-looking links first), pull and append their text.

Returns (text, status) where status feeds the record's `pdf_status` field.
Fail-soft: any network/parse error degrades to whatever text was gathered.

Rule respected downstream: no claim in an outreach email that isn't verified
in the document — full text here is what makes document-level findings possible.
"""

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from pdf_reader import get_pdf_text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}
PAGE_TIMEOUT = 30
MAX_LINKED_DOCS = 2          # cap PDF pulls per posting
MAX_DOC_CHARS = 60_000       # stay under analyze_rfp's 100K session cap
# Links whose text/href suggests the actual solicitation document
_DOC_HINT = re.compile(r"rfp|rfq|proposal|solicitation|bid|specification|scope", re.I)


def _is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def _fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=PAGE_TIMEOUT)
        resp.raise_for_status()
        if "text/html" not in resp.headers.get("Content-Type", "text/html"):
            return None
        return resp.text
    except Exception as e:
        print(f"    [!] Page fetch failed for {url[:60]}: {e}")
        return None


def _page_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse blank-line runs
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _candidate_doc_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Linked PDFs from the posting page, RFP-looking ones first."""
    pdfs: list[tuple[int, str]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if not _is_pdf_url(href) or href in seen:
            continue
        seen.add(href)
        label = f"{a.get_text(' ', strip=True)} {href}"
        priority = 0 if _DOC_HINT.search(label) else 1
        pdfs.append((priority, href))
    pdfs.sort(key=lambda p: p[0])
    return [href for _, href in pdfs]


def get_document_text(url: str) -> tuple[str | None, str]:
    """
    Pull the fullest text available for an opportunity link.

    Returns:
        (text, status) — text is None if nothing could be fetched.
        status examples: "PDF Analyzed", "Page + 2 PDFs", "Page only", "No PDF"
    """
    if not url or not url.startswith("http"):
        return None, "No PDF"

    # Case 1: the link is the document itself
    if _is_pdf_url(url):
        text, error = get_pdf_text(url)
        if text:
            return text[:MAX_DOC_CHARS], "PDF Analyzed"
        return None, f"PDF Error: {error}"

    # Case 2: HTML posting page — page text + linked documents
    html = _fetch_page(url)
    if html is None:
        return None, "No PDF"

    soup = BeautifulSoup(html, "html.parser")

    # Login-walled pages (CSDA /discussion/ details render the HigherLogic
    # login shell to non-members) carry no signal — don't pollute the analysis
    # text with form chrome. CSDA membership is a settled hard-no; full text
    # for those comes from the district's own site when resolved.
    if soup.find("input", attrs={"type": "password"}):
        return None, "Login wall"

    parts = []
    page_text = _page_text(soup)
    if page_text:
        parts.append(page_text)

    pulled = 0
    for doc_url in _candidate_doc_links(soup, url)[:MAX_LINKED_DOCS]:
        text, error = get_pdf_text(doc_url)
        if text:
            parts.append(f"\n--- LINKED DOCUMENT: {doc_url} ---\n{text}")
            pulled += 1
        else:
            print(f"    [!] Linked doc failed ({doc_url[:60]}): {error}")

    if not parts:
        return None, "No PDF"

    combined = "\n".join(parts)[:MAX_DOC_CHARS]
    if pulled:
        status = f"Page + {pulled} PDF{'s' if pulled > 1 else ''}"
    else:
        status = "Page only"
    return combined, status


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.csda.net/career-center/rfp-clearinghouse"
    text, status = get_document_text(test_url)
    print(f"STATUS: {status}")
    print(f"CHARS:  {len(text) if text else 0}")
    if text:
        print(text[:500])
