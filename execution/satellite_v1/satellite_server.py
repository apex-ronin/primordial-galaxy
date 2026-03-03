import os
import subprocess
import json
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Satellite-01 Dashboard")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Task tracking
STATUS_FILE = "saturation_status.json"
LOG_FILE = "saturation_run.log"

def update_status(status, message=None, data=None):
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "status": status,
            "message": message,
            "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": data
        }, f)

@app.get("/", response_class=HTMLResponse)
async def read_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=404, detail="Dashboard UI not found")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/health")
async def check_health():
    try:
        result = subprocess.run(
            ["python3", "execution/health_check.py"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        return {"status": "success", "output": result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_saturation_background():
    update_status("Running", "Federal RFP saturation cycle in progress...")
    try:
        with open(LOG_FILE, "w") as log:
            process = subprocess.Popen(
                ["python3", "execution/main.py"],
                stdout=log,
                stderr=log,
                cwd=os.getcwd(),
                text=True
            )
            process.wait()
        
        if process.returncode == 0:
            # Try to load results
            opps_file = "opportunities.json"
            data = []
            if os.path.exists(opps_file):
                with open(opps_file, "r") as f:
                    data = json.load(f)
            update_status("Finished", "Saturation cycle complete.", data=data[:10])
        else:
            update_status("Failed", f"Process exited with code {process.returncode}")
    except Exception as e:
        update_status("Error", str(e))

@app.post("/api/initiate")
async def initiate_saturation(background_tasks: BackgroundTasks):
    # Check if already running
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            current = json.load(f)
            if current.get("status") == "Running":
                return {"status": "already_running", "message": "A cycle is already in progress."}
    
    background_tasks.add_task(run_saturation_background)
    return {"status": "success", "message": "Saturation cycle initiated in background."}

@app.get("/api/status")
async def get_status():
    if not os.path.exists(STATUS_FILE):
        return {"status": "Idle", "message": "No saturation cycle has been run yet."}
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
