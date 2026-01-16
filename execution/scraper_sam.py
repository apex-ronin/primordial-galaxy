import requests
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SAM.gov API endpoint (from official documentation - v2 endpoint)
API_BASE = "https://api.sam.gov/opportunities/v2/search"
API_KEY = os.getenv("SAM_API_KEY")

def fetch_federal_opportunities():
    """
    Fetches active Federal 'Small Business Set-Aside' opportunities from SAM.gov.
    Uses direct API calls (no browser needed).
    """
    print(f"[*] Connecting to SAM.gov API (Federal Hunter)...")
    print(f"    Target: Total Small Business Set-Asides")
    
    opportunities = []
    
    try:
        # API parameters (from official documentation)
        # Date range is mandatory per API docs
        from_date = datetime.now().replace(day=1).strftime("%m/%d/%Y")
        to_date = datetime.now().strftime("%m/%d/%Y")
        
        params = {
            "api_key": API_KEY,  # API key as URL parameter
            "limit": 25,
            "offset": 0,
            "postedFrom": from_date,
            "postedTo": to_date,
            "ptype": "o",  # Combined Synopsis/Solicitation
            "active": "true"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        print(f"    [*] Sending API request...")
        print(f"    Date range: {from_date} to {to_date}")
        response = requests.get(API_BASE, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract opportunities
            if "opportunitiesData" in data:
                results = data["opportunitiesData"]
                print(f"    [OK] Found {len(results)} opportunities!")
                
                for item in results:
                    # Filter for Small Business Set-Asides
                    set_aside = item.get("typeOfSetAside", "")
                    if set_aside and "SB" in set_aside.upper():  # SBA, SBP, etc
                        opp = {
                            "title": item.get("title", "N/A"),
                            "agency": item.get("department", "N/A"),
                            "notice_id": item.get("noticeId", "N/A"),
                            "posted_date": item.get("postedDate", "N/A"),
                            "response_deadline": item.get("responseDeadLine", "N/A"),
                            "set_aside": set_aside,
                            "link": f"https://sam.gov/opp/{item.get('noticeId', '')}/view",
                            "source": "SAM.gov (Federal)",
                            "naics": item.get("naicsCode", "N/A")
                        }
                        opportunities.append(opp)
                
                print(f"    [OK] Filtered to {len(opportunities)} Small Business opportunities")
            else:
                print(f"    [!] Unexpected API response structure")
                print(f"    Response keys: {list(data.keys())}")
        else:
            print(f"    [!] API Error: {response.status_code}")
            print(f"    Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("[!] API request timed out")
    except requests.exceptions.RequestException as e:
        print(f"[!] API request failed: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
    
    return opportunities

if __name__ == "__main__":
    opps = fetch_federal_opportunities()
    
    print(f"\n{'='*60}")
    print(f"FEDERAL HUNTER RESULTS: {len(opps)} opportunities")
    print(f"{'='*60}\n")
    
    for idx, opp in enumerate(opps, 1):
        print(f"{idx}. {opp['title']}")
        print(f"   Agency: {opp['agency']}")
        print(f"   Deadline: {opp['response_deadline']}")
        print(f"   Set-Aside: {opp['set_aside']}")
        print(f"   Link: {opp['link']}\n")
