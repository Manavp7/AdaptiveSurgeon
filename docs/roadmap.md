# Roadmap

## M1 — Connected vertical slice ✅ (this repository)

End-to-end workflow with synthetic/heuristic providers, runnable offline on one
machine:

- Surgical Data Platform (Patient→Procedure→Media→Event→Outcome) + object storage
- Video Intelligence (instrument detection + tracking + analytics)
- Procedure timeline, Skill Engine, Risk Engine, Copilot (advisory)
- Digital Twin viewer (Three.js), Foundation / case search scaffold
- Unified dashboard, minimal RBAC, single-command setup, tests + smoke test

## M1.5 — Platform expansion ✅ (this repository)

Async analysis jobs + progress; anatomy overlays; intra-op vitals; per-instrument
& vitals charts; outcome editor; annotations; CSV/JSON export; dashboard
filters; surgeon scorecards/leaderboard; comparative case view; **Live OR
WebSocket replay**; **trainable scikit-learn risk/phase models (M4) with
fallback**; **DICOM-lite CT slice viewer**; minimal RBAC + token refresh; audit
log; consent + PHI de-id; pagination; provider capability reporting; S3/MinIO
adapter; Dockerfiles + compose. All offline-first with synthetic fallbacks.

## M3 — Real Medical Imaging + Surgical Planning ✅ (this repository)

Replaced synthetic imaging with **real DICOM** (CT in Hounsfield units + real MR
volume, bundled offline via pydicom) and a **PACS-grade viewer** (window/level
presets, axial/coronal/sagittal MPR, zoom, HU readout, mm measurement, metadata).
Added **surgical approach planning & simulation** (trajectory clearance to
critical structures, safety score, warnings, animated probe) plus an honest
**simulation-only, non-autonomous** teleoperation preview. The system explicitly
does not perform surgery.

## M2 — Real Video Intelligence

Integrate a trained surgical instrument detector (YOLO/RT-DETR) via the existing
`InstrumentDetectionProvider`; ONNX runtime; tracking evaluation on labeled data.

## M3 — Anatomy Segmentation

`AnatomySegmentationProvider` backed by SAM / Mask2Former fine-tuned on surgical
data; accurate Safe/Caution/Critical overlays composited on the live feed.

## M4 — Procedure & Risk ML

Temporal video transformer for phase recognition; outcome-trained multimodal risk
model; experiment tracking (MLflow); evaluation harness.

## M5 — Digital Twin

DICOM ingestion, volume rendering, segmentation, and intra-op registration for
true expected-vs-actual comparison.

## M6 — Foundation Model + Multi-tenant Deployment

Embeddings at scale, RAG over the outcome database, PostgreSQL + MinIO + K8s,
auth/audit/PHI de-identification, multi-site federation.

## Out of scope (documentation only)

**Subsystem 10 — Autonomous Assistance** (smart camera, smart navigation, robotic
integration). Requires robotics partnerships, extensive safety cases, and
regulatory clearance. Helping, never replacing, surgeons.
