# Primordial Galaxy: GovTech Hunter (Cloud V2)

> Production-grade government contract intelligence and Red Team simulation system. Optimized for **Cloud Stability** and **CSDA Honey Pot** discovery.

## 🏗 High-Fidelity Architecture

This repository is organized to separate strategy, orchestration, and execution:

- **Layer 1: Directives (`directives/`)**
  - [Satellite Dashboard Ops (Cloud V2)](directives/satellite_dashboard_ops.md)
  - [CSDA Honey Pot SOP](directives/csda_honey_pot.md)
  - [SSH Troubleshooting Guide](directives/troubleshooting_ssh.md)
- **Layer 2: Orchestration**
  - **Non-blocking Server**: FastAPI background tasks for long-running discovery.
  - **Status Polling**: Real-time feedback loop between Dashboard and Node.
- **Layer 3: Execution (`execution/`)**
  - **Primary Discovery**: `scraper_csda.py` (Honey Pot), `scraper_sam.py` (Whale).
  - **Filtering**: `discovery_engine.py` (Vertex AI Search Integration).
  - **Interface**: `satellite_v1/dashboard.html` (Orbital Command UI).

## 🚀 Cloud Operations

### 1. The SSH Bridge

All cloud interaction must use the authorized Google account identifier:

```bash
gcloud compute ssh jsn.nlsn@pureswarm-node --zone=us-central1-a --project=pureswarm-fortress
```

### 2. Launch the Satellite-01 (V2)

The dashboard server should be run as a background process on the VM:

```bash
nohup ./venv/bin/python3 execution/satellite_v1/satellite_server.py > satellite_server.log 2>&1 &
```

Access the Orbital Command Center at [**`http://35.222.150.190:8080`**](http://35.222.150.190:8080).

### 3. Verification

Use the **"Run Diagnostics"** button in the dashboard to verify the heartbeat of Vertex AI, SAM.gov, Gemini, and the CSDA Clearinghouse.

## 📜 Session History

- **Phase 3.5**: Hardened cloud stability, resolved subprocess "hangs," integrated CSDA specialized scraper, and restored high-fidelity "Orbital" animations.
