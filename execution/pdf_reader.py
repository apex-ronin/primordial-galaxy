import requests
import json
from pypdf import PdfReader
from io import BytesIO
import hashlib
import os

CACHE_DIR = "pdf_cache"

def get_cache_path(url):
    """Generate a cache filename based on URL hash."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.txt")

def download_pdf(url):
    """Download PDF from URL and return bytes."""
    print(f"    [*] Downloading PDF from {url[:50]}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"    [!] Download failed: {e}")
        return None

def extract_text(pdf_bytes):
    """Extract text from PDF bytes using pypdf."""
    try:
        pdf_file = BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception as e:
                print(f"    [!] Error reading page {page_num}: {e}")
                continue
        
        full_text = "\n".join(text_parts)
        
        if not full_text.strip():
            return None, "Empty or scanned PDF (no text found)"
        
        return full_text, None
    
    except Exception as e:
        return None, f"PDF parsing error: {e}"

def get_pdf_text(url, use_cache=True):
    """
    Download and extract text from a PDF URL.
    Uses cache to avoid re-downloading.
    
    Returns: (text, error_message)
    """
    # Check cache first
    if use_cache:
        cache_path = get_cache_path(url)
        if os.path.exists(cache_path):
            print(f"    [*] Using cached text for {url[:50]}...")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read(), None
    
    # Download PDF
    pdf_bytes = download_pdf(url)
    if not pdf_bytes:
        return None, "Download failed"
    
    # Extract text
    text, error = extract_text(pdf_bytes)
    
    # Cache the result if successful
    if text and use_cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_path = get_cache_path(url)
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"    [*] Cached text ({len(text)} chars)")
    
    return text, error

if __name__ == "__main__":
    # Test with a known PDF URL from our discovery results
    test_url = "https://www.lakecountyca.gov/DocumentCenter/View/11754/RFP-On-Call-Engineering-Services-August-2024"
    
    text, error = get_pdf_text(test_url)
    
    if error:
        print(f"ERROR: {error}")
    else:
        print(f"SUCCESS: Extracted {len(text)} characters")
        print(f"\nFirst 500 chars:\n{text[:500]}")
