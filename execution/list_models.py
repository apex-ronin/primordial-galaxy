import os
from google.cloud import aiplatform
from vertexai.preview.language_models import TextGenerationModel

# Initialize Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "project-140f6f73-bf22-4081-a65")
LOCATION = "us-central1"

print(f"[*] Checking available models for project: {PROJECT_ID} in {LOCATION}...")

try:
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    
    # Method 1: Try to list Foundation Models
    print("\n--- Attempting to list Foundation Models ---")
    try:
        models = aiplatform.Model.list()
        if not models:
            print("No custom models found (expected for new project).")
        for model in models:
            print(f"Found Model: {model.display_name} ({model.resource_name})")
    except Exception as e:
        print(f"Error listing custom models: {e}")

    # Method 2: Test specific known models to see which one doesn't crash
    print("\n--- Testing Access to Specific Models ---")
    
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "text-bison",       # PaLM 2 (Legacy but reliable)
        "text-bison@001",
        "text-bison@002"
    ]
    
    from vertexai.generative_models import GenerativeModel
    
    for model_name in candidates:
        print(f"Testing {model_name}...", end=" ")
        try:
            if "bison" in model_name:
                # PaLM 2 uses a different class
                model = TextGenerationModel.from_pretrained(model_name)
                print("Initialized...", end=" ")
                response = model.predict("Hello", max_output_tokens=5)
                print(f"SUCCESS! Response: {response.text}")
            else:
                # Gemini uses GenerativeModel
                model = GenerativeModel(model_name)
                print("Initialized...", end=" ")
                response = model.generate_content("Hello", generation_config={"max_output_tokens": 5})
                print(f"SUCCESS! Response: {response.text}")
                
        except Exception as e:
            print(f"FAILED: {e}")

    print("\n[*] Diagnostic complete.")

except Exception as e:
    print(f"[!] Fatal Error: {e}")
