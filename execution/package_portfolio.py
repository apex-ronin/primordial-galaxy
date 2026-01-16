import zipfile
import os
import shutil

# Define paths
BRAIN_DIR = r"C:\Users\Jnel9\.gemini\antigravity\brain\def0f155-1765-41fa-af03-105e30b31b4c"
PLAYGROUND_DIR = r"C:\Users\Jnel9\.gemini\antigravity\playground\primordial-galaxy"
OUTPUT_ZIP = os.path.join(PLAYGROUND_DIR, "govtech_portfolio.zip")

# Files to include
DOCS = [
    "GovTech_Hunter_Portfolio.md",
    "whitepaper_outline.md",
    "risk_mitigation_memo.md",
    "deployment_strategy.md",
    "master_roadmap.md"
]

CODE_AND_DATA = [
    "threat_assessment.json",
    "opportunities.json",
    "main.py",
    "scraper_sam.py",
    "gemini_analyst.py",
    "red_team_simulation.py",
    "hunter_eyes.py",
    "hunter_brain.py",
    "pdf_reader.py",
    "discovery_engine.py"
]

def create_package():
    print(f"[*] Creating portfolio package at: {OUTPUT_ZIP}")
    
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add Documentation
        print("    Adding Documentation...")
        for doc in DOCS:
            src = os.path.join(BRAIN_DIR, doc)
            if os.path.exists(src):
                zipf.write(src, arcname=f"documentation/{doc}")
                print(f"    + {doc}")
            else:
                print(f"    ! Missing: {doc}")

        # Add Code & Data
        print("    Adding Code & Data...")
        for item in CODE_AND_DATA:
            src = os.path.join(PLAYGROUND_DIR, item)
            if os.path.exists(src):
                zipf.write(src, arcname=f"codebase/{item}")
                print(f"    + {item}")
            else:
                print(f"    ! Missing: {item}")
                
    print(f"[*] Package created successfully!")

if __name__ == "__main__":
    create_package()
