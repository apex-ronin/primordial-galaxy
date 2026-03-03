import zipfile
import os
import shutil

# Define paths
# Use the actual current working directory
PROJECT_ROOT = os.getcwd()
BRAIN_DIR = r"C:\Users\Jnel9\.gemini\antigravity\brain\def0f155-1765-41fa-af03-105e30b31b4c"
OUTPUT_ZIP = os.path.join(PROJECT_ROOT, "peer_review_package.zip")

# Documentation from Brain DB
DOCS_BRAIN = {
    "GovTech_Hunter_Portfolio.md": "README_Portfolio.md",
    "Nelson_Whitepaper_AI_Procurement_Security.md": "Whitepaper_The_Rise_of_the_Prompt_Kiddie.md",
    "risk_mitigation_memo.md": "Risk_Mitigation_Memo.md",
    "deployment_strategy.md": "Deployment_Strategy.md",
    "master_roadmap.md": "Master_Roadmap.md"
}

# Code from current workspace
CODE_SCRIPTS = [
    "execution/main.py",
    "execution/red_team_simulation.py",
    "execution/gemini_analyst.py",
    "execution/hunter_eyes.py",
    "execution/hunter_brain.py",
    "execution/scraper_sam.py",
    "execution/scraper_eldorado.py",
    "execution/orchestrator.py",
    "execution/pdf_reader.py",
    "execution/discovery_engine.py"
]

# Directives
DIRECTIVES = [
    "directives/git_publication_safety.md",
    "directives/red_team_analysis.md",
    "directives/saturation_philosophy.md",
    "README.md",
    "requirements.txt"
]

# Data
DATA_FILES = {
    "opportunities.json": "data/opportunities.json",
    "historical_archive/threat_assessment.json": "data/threat_assessment.json"
}

def create_package():
    print(f"[*] Creating peer review package at: {OUTPUT_ZIP}")
    
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add Documentation from Brain
        print("    Adding Documentation...")
        for src_name, dest_name in DOCS_BRAIN.items():
            src_path = os.path.join(BRAIN_DIR, src_name)
            if os.path.exists(src_path):
                zipf.write(src_path, arcname=f"documentation/{dest_name}")
                print(f"    + {dest_name}")
            else:
                print(f"    ! Missing in Brain: {src_name}")

        # Add Code Scripts
        print("    Adding Codebase...")
        for script in CODE_SCRIPTS:
            src_path = os.path.join(PROJECT_ROOT, script)
            if os.path.exists(src_path):
                zipf.write(src_path, arcname=f"codebase/{os.path.basename(script)}")
                print(f"    + {script}")
            else:
                print(f"    ! Missing script: {script}")

        # Add Directives
        print("    Adding Directives...")
        for directive in DIRECTIVES:
            src_path = os.path.join(PROJECT_ROOT, directive)
            if os.path.exists(src_path):
                zipf.write(src_path, arcname=f"directives/{os.path.basename(directive)}")
                print(f"    + {directive}")
            else:
                print(f"    ! Missing directive: {directive}")

        # Add Data
        print("    Adding Data...")
        for src_rel, arc_path in DATA_FILES.items():
            src_path = os.path.join(PROJECT_ROOT, src_rel)
            if os.path.exists(src_path):
                zipf.write(src_path, arcname=arc_path)
                print(f"    + {src_rel}")
            else:
                print(f"    ! Missing data file: {src_rel}")
                
    print(f"[*] Package created successfully: {OUTPUT_ZIP}")

if __name__ == "__main__":
    create_package()
