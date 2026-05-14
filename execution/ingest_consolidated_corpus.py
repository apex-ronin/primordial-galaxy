import os
import json
import re
from google.cloud import discoveryengine_v1beta as discoveryengine
from dotenv import load_dotenv

# Load env from primordial-galaxy
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, ".env"))

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "govtech-control")
LOCATION = "global"
DATA_STORE_ID = os.getenv("VERTEX_DATA_STORE_ID")

# Path to the consolidated JSONL in data-arsenal
CORPUS_JSONL = r"C:\Users\Jnel9\Workspaces\AI-Agents\Active\data-arsenal\data\raw\legal_corpus.jsonl"

def ingest_documents():
    if not DATA_STORE_ID:
        print("[!] VERTEX_DATA_STORE_ID is not set in environment.")
        return

    client_options = (
        {"api_endpoint": f"{LOCATION}-discoveryengine.googleapis.com"}
        if LOCATION != "global"
        else None
    )
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/branches/0"
    
    if not os.path.exists(CORPUS_JSONL):
        print(f"[!] Could not find {CORPUS_JSONL}")
        return

    documents = []
    print(f"[*] Reading consolidated corpus from {CORPUS_JSONL}")
    
    with open(CORPUS_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            doc = discoveryengine.Document()
            
            # Create a safe ID string
            safe_id = re.sub(r'[^a-zA-Z0-9-_]', '', str(item["id"]).replace(" ", "_").replace(".", "_").replace("-", "_"))
            doc.id = safe_id
            
            # Map fields for Discovery Engine
            # Note: We use 'snippet' for the main text and keep other metadata in struct_data
            content_text = item.get("clause_text") or item.get("content") or ""
            
            struct_data = {
                "title": item["title"],
                "corpus_type": item.get("corpus_type", "clause"),
                "vector": item.get("vector", ""),
                "snippet": content_text[:10000], # Discovery Engine snippet limit
                "link": f"legal_corpus_{safe_id}",
                "authority": item.get("authority", ""),
                "effective_date": item.get("effective_date", ""),
                "source_url": item.get("source_url", ""),
                "notes": item.get("notes", "")
            }
            
            doc.struct_data = struct_data
            doc.content = discoveryengine.Document.Content(
                mime_type="text/plain",
                raw_bytes=content_text.encode("utf-8")
            )
            documents.append(doc)
    
    if not documents:
        print("[!] No documents to ingest.")
        return
        
    print(f"[*] Submitting {len(documents)} documents to {parent} via InlineSource...")
    
    # Inline source has a limit (usually 100 docs per request or total size)
    # We'll batch them in groups of 50 just to be safe
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
            print(f"[*] LRO started for batch {i//batch_size + 1}. Waiting...")
            response = operation.result()
            print(f"[+] Batch {i//batch_size + 1} successful.")
        except Exception as e:
            print(f"[!] Ingestion failed for batch {i//batch_size + 1}: {e}")

if __name__ == "__main__":
    ingest_documents()
