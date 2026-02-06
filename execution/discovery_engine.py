import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX") # Search Engine ID

def search_google(query, num_results=10):
    """
    Uses Google Custom Search JSON API to find GovTech targets.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        print("[!] Error: Missing Google API Key or CX ID.")
        print("    Please set GOOGLE_API_KEY and GOOGLE_CX in your .env file.")
        return []

    print(f"[*] Searching Google for: '{query}'...")
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CX,
        'q': query,
        'num': num_results
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    results = []
    if 'items' in data:
        for item in data['items']:
            result = {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet")
            }
            results.append(result)
            print(f"    [+] Found: {result['title'][:50]}...")
    
    return results

if __name__ == "__main__":
    # Test Search
    # We look for "RFP" on .gov sites related to "special district"
    test_query = '"special district" "RFP" site:.gov filetype:pdf'
    results = search_google(test_query, num_results=5)
    print(json.dumps(results, indent=2))
