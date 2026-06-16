# Deployment (future / hardware)

This describes the eventual on-prem deployment. The current repository runs
entirely on a single machine without any of this hardware.

## Operating Room AI Box

A compact GPU appliance installed in the OR:

- **Compute:** NVIDIA Jetson AGX Orin (edge) or an RTX 6000 workstation (room).
- CPU / RAM / NVMe storage sized for real-time inference on 1080p/4K feeds.

## Video capture

- Receives the laparoscope feed via **HDMI** or **SDI**.
- Overlays are composited and shown on the **existing OR monitor** — no new
  display required.

## Storage

- Hospital-grade storage, **20–100 TB** per site eventually, for video + imaging
  + derived analytics.
- In software this is the object-storage abstraction (local → MinIO/S3).

## Networking

- Gigabit LAN within the hospital.
- Secure VPN + optional cloud sync for cross-site learning and the foundation
  model, subject to governance and de-identification.

## Software topology (future)

```
OR AI Box (edge inference)  ──►  Hospital server (Postgres + MinIO + API)
                                        │
                                        ▼
                            Cloud (foundation model, multi-site)
```

The included [`infra/docker-compose.yml`](../infra/docker-compose.yml) sketches
the hospital-server tier (Postgres, Redis, MinIO, API, frontend) for a future
containerized deployment. It is **not** required to run the prototype.

## Compliance prerequisites (before any clinical use)

PHI de-identification, consent management, audit logging, access control,
clinical validation, and regulatory clearance (FDA/CE/CDSCO). See
[`DISCLAIMER.md`](DISCLAIMER.md).
