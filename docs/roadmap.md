# Roadmap

## M1 — Connected vertical slice ✅ (this repository)

End-to-end workflow with synthetic/heuristic providers, runnable offline on one
machine:

- Surgical Data Platform (Patient→Procedure→Media→Event→Outcome) + object storage
- Video Intelligence (instrument detection + tracking + analytics)
- Procedure timeline, Skill Engine, Risk Engine, Copilot (advisory)
- Digital Twin viewer (Three.js), Foundation / case search scaffold
- Unified dashboard, minimal RBAC, single-command setup, tests + smoke test

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
