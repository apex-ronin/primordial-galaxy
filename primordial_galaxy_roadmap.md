# PRIMORDIAL GALAXY - Apex Ronin Roadmap

This is the single source of truth for the local `primordial-galaxy` repository.
*Goal*: Provide the underlying intelligence infrastructure for Apex Ronin's "GovTech Hunter" capabilities.

---

## RECENTLY COMPLETED (Session V10)
- [x] **GSAR 552.239-7001 Compliance**: Completely migrated `gemini_analyst.py`, `red_team_simulation.py`, and `antibody_agent.py` to **Vertex AI (GCP)**. 
- [x] **Vertex API Troubleshooting**: Resolved `us-central1` truncation bugs, switched to `gemini-2.5-flash`, and established 8192 token limit.
- [x] **DEI Executive Order (2026-03-26) Compliance**: Strict "Qualifications & Performance based" guards applied to prompt suffix.
- [x] **Whitepaper Preface**: Drafted the GTG-1002 "Stale-by-Default Paradigm".

## IMMEDIATE NEXT STEPS (To Do)
- [ ] **Entity & Domain Lock**: 
  - Register `apexronin.com` and `apexronin.com`.
  - Set up Google Workspace for `jay@apexronin.com` for compliant client communications.
- [ ] **Phase 4 - GovTech Shield Deployment**:
  - Secure first 5-star review via rescue service on Upwork/Freelancer.
  - Deploy GovTech Shield for initial RFP26-03 outreach to Early Incumbent Defense (EID) firms.
- [ ] **Finalize the GTG-1002 Whitepaper**: Expand the preface into the full whitepaper (using production runs from `threat_assessment.json` to prove "In-Flight Validation").

## PENDING DECISIONS (Needs Action)
- **Infrastructure Decommissioning**: The Hetzner Dashboard is noted as active but slated for decommissioning. Should we pull it down entirely and migrate all UI elements to a sovereign AWS/GCP node or keep it running headless?
- **Cloud Transition Plan**: The `ROADMAP.md` states "DO NOT migrate any GDrive assets until Workspace is live." Do we need an automated sync script or will that migration be completely manual once `apexronin.com` is active?

---
*For granular functional logic, reference `directives/functional_roadmap.md`.*
