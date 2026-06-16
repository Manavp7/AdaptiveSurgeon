# AdaptiveSurgeon

**A Surgical Intelligence Operating System** — *Copilot for Surgeons.*

AdaptiveSurgeon adds Computer Vision, Procedure Intelligence, Risk Prediction, a
Patient Digital Twin, a Knowledge Base, and Real-Time Guidance on top of the
surgical camera feed. This repository is a **coherent, end-to-end vertical
slice**: every subsystem is connected through **one workflow**, runnable on a
single machine, fully offline.

> ⚠️ **Research prototype — ADVISORY ONLY. Not a medical device.** All data is
> synthetic. No clinical claims are made. See [`docs/DISCLAIMER.md`](docs/DISCLAIMER.md).

---

## The connected workflow

```
Upload surgery
   ↓
Pipeline processes video        (Video Intelligence)
   ↓
Instruments detected / tracked  (detection + tracking + analytics)
   ↓
Procedure timeline generated    (phase recognition)
   ↓
Skill metrics generated         (Skill Engine)
   ↓
Risk events generated           (Risk Engine)
   ↓
Copilot recommendations         (advisory only)
   ↓
Digital twin displayed          (3D anatomy, expected vs actual)
   ↓
Unified dashboard shows everything
```

Each stage consumes the previous stage's output — this is one pipeline, not a
collection of disconnected demos.

## Quick start (single command)

```bash
bash scripts/setup.sh     # venv + backend deps + frontend deps + seed demo data
bash scripts/run_dev.sh   # backend :8000  +  frontend :5173
```

Then open **http://localhost:5173** and sign in:

| Role    | Username  | Password     | Can…                       |
|---------|-----------|--------------|----------------------------|
| surgeon | `surgeon` | `surgeon123` | full workflow (upload/analyze) |
| admin   | `admin`   | `admin123`   | + manage users             |
| viewer  | `viewer`  | `viewer123`  | read-only                  |

Other commands: `make test` (pytest), `make smoke` (end-to-end HTTP check),
`make build` (frontend production build), `make train` (train the optional
scikit-learn risk/phase models).

## Features

**Core workflow (M1):** data platform, video intelligence (detection + tracking),
procedure timeline, skill engine, risk engine, advisory copilot, digital twin,
foundation/case-search — all connected through one pipeline.

**Expanded (M2+):**
- **Async analysis jobs** with live progress (`POST /analyze` → `job_id`, poll `/jobs/{id}`)
- **Anatomy overlays** on the video (Safe/Caution/Critical segmentation)
- **Intra-op vitals** (HR/BP/SpO₂) correlated with the risk timeline
- **Per-instrument analytics** + **vitals charts** (dependency-free SVG)
- **Outcome editor**, **time-anchored annotations**, **CSV/JSON report export**
- **Dashboard filtering/search**; **surgeon scorecards & leaderboard**
- **Comparative case view** (synced side-by-side) and **Live OR** replay (WebSocket)
- **Trainable ML models (M4)**: scikit-learn risk + phase models (`make train`),
  selected via `ADAPTIVE_RISK_PROVIDER=model` / `ADAPTIVE_PHASE_PROVIDER=model`,
  with automatic fallback to rules/heuristics
- **Real medical imaging (M3):** loads **real DICOM** studies (CT in Hounsfield
  units + a real MR volume, bundled offline via pydicom) into a **PACS-grade
  viewer** — window/level presets, axial/coronal/sagittal **MPR**, zoom, **HU
  readout**, **mm distance measurement**, and a DICOM metadata panel
- **Surgical planning & simulation (M3):** plan an instrument approach on the 3D
  twin; computes clearance to each critical structure, a safety score, and
  warnings; animates the trajectory. **Honest boundary:** this is planning/
  simulation and a **simulation-only, non-autonomous** teleoperation preview —
  the system does **not** perform surgery or drive any robot.
- **Minimal RBAC** + **token refresh**, **audit log**, **consent + PHI de-id**
- **Pagination**; **provider capability reporting** (`/api/providers`)
- **S3/MinIO storage adapter** (optional) and **Dockerfiles + compose** (deploy-only)

## Architecture at a glance

- **Backend** — FastAPI + SQLAlchemy. SQLite by default; PostgreSQL-ready via
  `ADAPTIVE_DATABASE_URL`. Local object storage abstraction (MinIO/S3-ready).
- **Frontend** — React + TypeScript + Vite, Three.js for the digital twin.
- **AI providers** — every intelligence module is behind a stable interface with
  a **synthetic/heuristic default** that runs offline, and an optional real-model
  path (YOLO / SAM / transformer / sentence-transformer) that drops in via config
  with no architectural change:
  `InstrumentDetectionProvider`, `AnatomySegmentationProvider`,
  `ProcedurePhaseProvider`, `RiskAssessmentProvider`, `CopilotProvider`,
  `EmbeddingProvider`.
- **Synthetic data** — deterministic generator creates surgical videos, patients,
  procedures, outcomes and reports. Ingestion goes through the same interfaces
  real de-identified hospital data would use.

See [`docs/architecture.md`](docs/architecture.md), [`docs/vision.md`](docs/vision.md),
[`docs/deployment.md`](docs/deployment.md), [`docs/business.md`](docs/business.md),
and [`docs/roadmap.md`](docs/roadmap.md).

## Repository layout

```
backend/    FastAPI app: data platform, providers, services, pipeline, seed, tests
frontend/   React/TS/Vite dashboard (video overlay, timeline, skill, risk, copilot, twin)
docs/        vision, architecture, deployment, business, roadmap, disclaimer
infra/       docker-compose (Postgres/Redis/MinIO) for future deployment
scripts/     setup.sh, run_dev.sh, smoke_test.sh
```

## Requirements

Python 3.11+, Node 18+. No GPU, Docker, or internet required to run. ffmpeg is
used (if present) to encode browser-playable H.264 video; otherwise an OpenCV
fallback is used.
