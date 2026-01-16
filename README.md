# Primordial Galaxy: GovTech Hunter

> Production-grade government contract intelligence and Red Team simulation system.

## 🏗 3-Layer Architecture

This repository is organized to separate strategy, orchestration, and execution:

- **Layer 1: Directives (`directives/`)**
  - Standard Operating Procedures (SOPs) for the system.
  - [Red Team Analysis SOP](directives/red_team_analysis.md)
- **Layer 2: Orchestration**
  - Handled by the AI agent through decision-making and tool calls.
- **Layer 3: Execution (`execution/`)**
  - Deterministic Python scripts that perform the heavy lifting.
  - Core scripts include `main.py` (Gathering) and `red_team_simulation.py` (Analysis).

## 📁 Project Structure

- `execution/`: Python tools/scripts.
- `directives/`: Natural language instruction sets.
- `historical_archive/`: Logs and files documenting the early development (original "messy" phase).
- `.tmp/`: Intermediate processing files.
- `logs/`: Technical execution logs.

## 🚀 Getting Started

1. Set up your environment:

   ```powershell
   # Copy example env
   cp .env.example .env
   # Add your GEMINI_API_KEY
   ```

2. Run the main discovery engine:

   ```powershell
   python execution/main.py
   ```

3. Run the security analysis:

   ```powershell
   python execution/red_team_simulation.py
   ```

## 📜 History

This project was born out of a rapid development phase aimed at proving the capabilities of agentic systems in the GovTech sector. The full paper trail of its evolution is preserved in `historical_archive/`.
