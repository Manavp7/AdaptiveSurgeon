# Architecture

AdaptiveSurgeon is built **data-platform-first**: clean schemas, an event model,
and storage are the foundation every intelligence subsystem plugs into. The
durable value (per the vision) is the *data network + outcome database +
foundation model*, not any single model — so the architecture makes models
swappable and the data layer central.

## System overview

```mermaid
flowchart TB
    subgraph Frontend["Frontend — React / TS / Vite"]
        DASH[Dashboard] --- DETAIL[Procedure Detail]
        DETAIL --- TWIN3D[Three.js Digital Twin]
        SEARCH[Case Search]
    end

    subgraph API["Backend — FastAPI"]
        AUTH[Auth / RBAC]
        DP[(Data Platform\nPatient→Procedure→Media→Event→Outcome)]
        PIPE[Analysis Pipeline]
        FND[Foundation / Case Search]
    end

    subgraph Providers["Swappable AI Providers"]
        IDP[InstrumentDetection]
        ASP[AnatomySegmentation]
        PPP[ProcedurePhase]
        RAP[RiskAssessment]
        CPP[Copilot]
        EMP[Embedding]
    end

    STORE[(Object Storage\nlocal → MinIO/S3)]
    DB[(SQLite → PostgreSQL)]

    Frontend -->|/api| API
    API --> DB
    DP --> STORE
    PIPE --> IDP & ASP & PPP & RAP & CPP
    FND --> EMP
    PIPE --> DB
```

## The connected pipeline (`services/pipeline.py`)

```mermaid
flowchart LR
    V[Video in storage] --> D[Detect instruments]
    D --> T[Track + motion analytics]
    T --> P[Phase timeline]
    P --> S[Skill score]
    P --> R[Risk timeline]
    R --> C[Copilot advisories]
    P --> TW[Digital twin]
    S --> E[Case embedding]
    D --> E
    E --> KB[(Knowledge base)]
```

Each subsystem consumes the previous one's output and persists results, so the
dashboard renders **one connected story** per procedure via a single
`GET /api/procedures/{id}/analysis` payload.

## Data model (Subsystem 1)

```
Patient ──< Procedure ──< Media (video / ct / mri / ...)
                 │            └──< Detection, Track
                 ├──< Event (phase | advisory | risk | complication | annotation)
                 ├──< PhaseSegment, SkillReport, RiskAssessment
                 ├──< DigitalTwin
                 ├──< CaseEmbedding
                 └──1 Outcome
```

UUID primary keys, JSON payload columns for flexibility, timestamps. All access
through SQLAlchemy so SQLite (dev) and PostgreSQL (prod) use identical code.

## Provider abstraction (the "OS" seam)

`backend/app/providers/` defines six ABCs and a config-driven registry
(`get_*_provider()`). Synthetic/heuristic implementations are the registered
defaults and always run offline. Optional real models are attempted only when
configured (env: `ADAPTIVE_INSTRUMENT_PROVIDER=yolo`, etc.) and fall back to the
synthetic provider on any import/load failure — the platform never breaks
offline.

| Interface | Default (offline) | Drop-in real model |
|-----------|-------------------|--------------------|
| InstrumentDetectionProvider | `SyntheticDetector` (HSV) | `YoloDetector` (ultralytics) |
| AnatomySegmentationProvider | `SyntheticAnatomy` | `SamSegmenter` (SAM) |
| ProcedurePhaseProvider | `HeuristicPhases` | temporal transformer |
| RiskAssessmentProvider | `RuleRisk` | trained multimodal model |
| CopilotProvider | `RuleCopilot` | LLM |
| EmbeddingProvider | `HashingTfidfEmbedder` | `SentenceTransformerEmbedder` |

## Ingestion & extensibility

Media is ingested through the object-storage interface and the relational
models — the exact path real de-identified hospital data will use. Adding real
data or real models requires **no architectural change**: implement a provider
or push records through the existing APIs.
