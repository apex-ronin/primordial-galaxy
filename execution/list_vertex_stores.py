from google.cloud import discoveryengine_v1beta as discoveryengine
import os
from dotenv import load_dotenv

load_dotenv()

project_id = "govtech-control"
location = "global"

def list_engines():
    client = discoveryengine.EngineServiceClient()
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"
    
    print(f"[*] Listing engines for {parent}...")
    try:
        response = client.list_engines(parent=parent)
        for engine in response:
            print(f"    - ID: {engine.name.split('/')[-1]}")
            print(f"      Display Name: {engine.display_name}")
            print(f"      Data Store IDs: {engine.data_store_ids}")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    list_engines()
