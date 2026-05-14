import os
import json
import re
from google.cloud import discoveryengine_v1beta as discoveryengine
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "govtech-control")
LOCATION = "global" # Discovery Engine data stores are in global, despite VERTEX_LOCATION env var
DATA_STORE_ID = os.getenv("VERTEX_DATA_STORE_ID")

def ingest_documents():
    if not DATA_STORE_ID:
        print("[!] VERTEX_DATA_STORE_ID is not set in environment.")
        # Fallback to listing data stores if not provided, or prompt user.
        print("Please ensure VERTEX_DATA_STORE_ID is in your .env")
        return

    client_options = (
        {"api_endpoint": f"{LOCATION}-discoveryengine.googleapis.com"}
        if LOCATION != "global"
        else None
    )
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/branches/0"
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    corpus_dir = os.path.join(base_dir, "data", "legal_corpus")
    files = sorted([
        os.path.join(corpus_dir, f)
        for f in os.listdir(corpus_dir)
        if f.endswith(".json")
    ])
    documents = []
    
    for f_path in files:
        if not os.path.exists(f_path):
            print(f"[!] Could not find {f_path}")
            continue
        with open(f_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                doc = discoveryengine.Document()
                # Create a safe ID string
                safe_id = re.sub(r'[^a-zA-Z0-9-_]', '', str(item["id"]).replace(" ", "_").replace(".", "_").replace("-", "_"))
                doc.id = safe_id
                
                # Struct data allows arbitrary JSON
                # Must provide required fields depending on schema, but struct_data is flexible for unstructured with metadata
                struct_data = {
                    "title": item["title"],
                    "vector": item.get("vector", ""),
                    "snippet": item["clause_text"],
                    "link": f"legal_corpus_{safe_id}"
                }
                # For unstructured datastores, content (raw_bytes) is required.
                doc.struct_data = struct_data
                doc.content = discoveryengine.Document.Content(
                    mime_type="text/plain",
                    raw_bytes=item["clause_text"].encode("utf-8")
                )
                documents.append(doc)
    
    if not documents:
        print("[!] No documents to ingest.")
        return
        
    print(f"[*] Submitting {len(documents)} documents to {parent} via InlineSource...")
    
    # Inline source has a limit of 100 documents per request.
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        print(f"[*] Submitting batch {i//batch_size + 1} ({len(batch)} docs)...")
        
        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            inline_source={"documents": batch}
        )
        
        try:
            operation = client.import_documents(request=request)
            print(f"[*] LRO started for batch {i//batch_size + 1}. Waiting for completion...")
            response = operation.result()
            print(f"[+] Batch {i//batch_size + 1} successful.")
        except Exception as e:
            print(f"[!] Ingestion failed for batch {i//batch_size + 1}: {e}")

if __name__ == "__main__":
    ingest_documents()
