import os
import json
from google.cloud import discoveryengine_v1beta as discoveryengine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VERTEX_LOCATION", "global")
DATA_STORE_ID = os.getenv("VERTEX_DATA_STORE_ID")

def search_vertex(query, num_results=10):
    """
    Uses Vertex AI Search (Discovery Engine) to find GovTech targets.
    """
    if not PROJECT_ID or not DATA_STORE_ID:
        print("[!] Error: Missing Project ID or Vertex Data Store ID.")
        return []

    print(f"[*] Searching Vertex AI Search for: '{query}'...")
    
    # Initialize client
    client = discoveryengine.SearchServiceClient()

    # The full resource name of the search engine serving config
    serving_config = client.serving_config_path(
        project=PROJECT_ID,
        location=LOCATION,
        data_store=DATA_STORE_ID,
        serving_config="default_config",
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=num_results,
    )

    try:
        response = client.search(request)
        results = []
        
        # Iterate over results
        for result in response.results:
            document = result.document
            derived_struct_data = document.derived_struct_data
            
            # Extract title and link from derived data
            title = derived_struct_data.get("title", "N/A")
            link = derived_struct_data.get("link", "N/A")
            snippet = derived_struct_data.get("snippets", [{}])[0].get("snippet", "N/A") if derived_struct_data.get("snippets") else "N/A"
            
            res = {
                "title": title,
                "link": link,
                "snippet": snippet
            }
            results.append(res)
            print(f"    [+] Found: {title[:50]}...")

        return results
    except Exception as e:
        print(f"[!] Vertex Search Error: {e}")
        return []

if __name__ == "__main__":
    # Test Search
    test_query = '"special district" "RFP" site:.gov filetype:pdf'
    results = search_vertex(test_query, num_results=5)
    print(json.dumps(results, indent=2))
