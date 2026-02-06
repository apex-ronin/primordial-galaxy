import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_google_api():
    print("[*] Checking Google Search API...")
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX")
    
    if not api_key:
        return False, "Missing GOOGLE_API_KEY"
    if not cx:
        return False, "Missing GOOGLE_CX"
        
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cx,
        'q': 'test',
        'num': 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def check_sam_api():
    print("[*] Checking SAM.gov API...")
    api_key = os.getenv("SAM_API_KEY")
    
    if not api_key:
        return False, "Missing SAM_API_KEY"
        
    # Simple check - just see if we can hit the endpoint, even if auth fails it's a connection check
    # But ideally we want to check auth. 
    # Using a known safe endpoint/params if possible, or just the search one with minimal params.
    url = "https://api.sam.gov/opportunities/v2/search"
    params = {
        "api_key": api_key,
        "limit": 1,
        "postedFrom": "01/01/2026",
        "postedTo": "01/02/2026", 
        "active": "true"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        # 403/401 means key is bad. 200 is good.
        if response.status_code == 200:
             return True, "OK"
        else:
             return False, f"Status: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return False, str(e)

def check_gemini_api():
    print("[*] Checking Gemini API...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
         return False, "Missing GEMINI_API_KEY"
    
    # We can't easily curl gemini without the lib usually, but we can try a simple imports check
    # or just assume if env is there it's likely OK, or do a small generation
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        # generating 1 token is cheap
        response = model.generate_content("Hi", generation_config=genai.types.GenerationConfig(max_output_tokens=1))
        if response:
            return True, "OK"
        return False, "No response from Gemini"
    except Exception as e:
        return False, str(e)

def run_all_checks():
    print("="*40)
    print("     SYSTEM HEALTH CHECK")
    print("="*40)
    
    results = {
        "Google Search": check_google_api(),
        "SAM.gov": check_sam_api(),
        "Gemini AI": check_gemini_api()
    }
    
    print("-" * 40)
    all_passed = True
    for name, (passed, msg) in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} | {name}: {msg}")
        if not passed:
            all_passed = False
    print("-" * 40)
    
    return all_passed

if __name__ == "__main__":
    run_all_checks()
