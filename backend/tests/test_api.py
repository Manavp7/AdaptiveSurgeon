"""API contract + RBAC + unified-workflow integration tests."""

from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["providers"]) == {
        "instrument", "anatomy", "phase", "risk", "copilot", "embedding"
    }


def test_rbac_enforced(client, viewer_token):
    # anonymous write -> 401
    assert client.post("/api/patients", json={"external_mrn": "x"}).status_code == 401
    # viewer write -> 403
    r = client.post(
        "/api/patients",
        json={"external_mrn": "x", "display_name": "x"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403


def test_pagination(client):
    page = client.get("/api/procedures?limit=1&offset=0").json()
    assert set(page) == {"items", "total", "limit", "offset"}
    assert len(page["items"]) == 1
    assert page["total"] >= 2
    assert page["limit"] == 1


def test_procedure_linked_graph(client):
    procs = client.get("/api/procedures").json()["items"]
    assert len(procs) >= 2
    detail = client.get(f"/api/procedures/{procs[0]['id']}").json()
    assert detail["patient"]["id"] == detail["patient_id"]
    assert len(detail["media"]) == 1
    assert detail["outcome"] is not None


def test_unified_analysis_connects_all_subsystems(client):
    procs = client.get("/api/procedures").json()["items"]
    pid = procs[0]["id"]
    a = client.get(f"/api/procedures/{pid}/analysis").json()
    assert a["status"] == "analyzed"
    assert a["video_uri"]
    assert len(a["phases"]) == 6           # procedure timeline
    assert len(a["tracks"]) > 0            # tracking
    assert a["detection_count"] > 0        # detection
    assert a["skill"]["score"] > 0         # skill
    assert len(a["risks"]) > 0             # risk
    assert len(a["advisories"]) > 0        # copilot
    assert len(a["anatomy"]) > 0           # anatomy segmentation overlay


def test_report_export(client):
    pid = client.get("/api/procedures").json()["items"][0]["id"]
    rep = client.get(f"/api/procedures/{pid}/report").json()
    assert rep["skill_score"] is not None
    assert rep["phases"] and rep["disclaimer"]
    # de-identified: no raw MRN in report
    assert "external_mrn" not in rep["patient"]
    csv_res = client.get(f"/api/procedures/{pid}/report.csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "skill_score" in csv_res.text


def test_vitals_generated_and_correlated(client):
    procs = client.get("/api/procedures").json()["items"]
    pid = procs[0]["id"]
    v = client.get(f"/api/procedures/{pid}/vitals").json()
    assert v["source"] == "synthetic"
    assert len(v["series"]) > 0
    pt = v["series"][0]
    assert {"t", "hr", "bp_sys", "bp_dia", "spo2"} <= set(pt)
    # SpO2 stays in a physiological band
    assert all(80 <= p["spo2"] <= 100 for p in v["series"])


def test_twin_and_foundation(client):
    procs = client.get("/api/procedures").json()["items"]
    pid = procs[0]["id"]
    twin = client.get(f"/api/procedures/{pid}/twin").json()
    assert len(twin["structures"]) > 0
    assert len(twin["expected_vs_actual"]) > 0

    sim = client.get(f"/api/foundation/similar?procedure_id={pid}").json()
    assert len(sim["results"]) > 0

    ask = client.post("/api/foundation/ask", json={"question": "complications?"}).json()
    assert ask["answer"]
    assert "provider" in ask


def test_reanalysis_is_idempotent(client, surgeon_token):
    procs = client.get("/api/procedures").json()["items"]
    pid = procs[0]["id"]
    h = {"Authorization": f"Bearer {surgeon_token}"}
    r1 = client.post(f"/api/procedures/{pid}/analyze?wait=true", headers=h).json()
    a = client.get(f"/api/procedures/{pid}/analysis").json()
    # re-running does not duplicate phase segments (still exactly 6)
    assert len(a["phases"]) == 6
    assert r1["phases"] == 6


def test_phi_deid_on_patient_create(client, surgeon_token):
    h = {"Authorization": f"Bearer {surgeon_token}"}
    r = client.post(
        "/api/patients",
        json={"external_mrn": "MRN-DEID-1", "display_name": "De-id Test",
              "consent_obtained": True, "consent_reference": "C-1"},
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["mrn_hash"].startswith("anon_")  # pseudonymized
    assert body["consent_obtained"] is True


def test_audit_log_records_writes_admin_only(client, surgeon_token):
    # generate an auditable write
    h = {"Authorization": f"Bearer {surgeon_token}"}
    client.post("/api/patients", json={"external_mrn": "MRN-AUD", "display_name": "Aud"}, headers=h)
    # surgeon cannot read audit
    assert client.get("/api/audit", headers=h).status_code == 403
    # admin can
    at = client.post("/api/auth/login", data={"username": "admin", "password": "admin123"}).json()["access_token"]
    page = client.get("/api/audit", headers={"Authorization": f"Bearer {at}"}).json()
    assert page["total"] >= 1
    assert any(e["path"].endswith("/patients") and e["method"] == "POST" for e in page["items"])


def test_annotations_crud(client, surgeon_token):
    h = {"Authorization": f"Bearer {surgeon_token}"}
    pid = client.get("/api/procedures").json()["items"][0]["id"]
    # create annotation
    r = client.post(
        f"/api/procedures/{pid}/events",
        json={"kind": "annotation", "label": "Check CVS here", "t_start_s": 12.0, "severity": "info"},
        headers=h,
    )
    assert r.status_code == 201
    eid = r.json()["id"]
    # list filtered by kind
    anns = client.get(f"/api/procedures/{pid}/events?kind=annotation").json()
    assert any(e["id"] == eid for e in anns)
    # delete (surgeon)
    assert client.delete(f"/api/procedures/{pid}/events/{eid}", headers=h).status_code == 204
    anns2 = client.get(f"/api/procedures/{pid}/events?kind=annotation").json()
    assert not any(e["id"] == eid for e in anns2)


def test_token_refresh(client, surgeon_token):
    h = {"Authorization": f"Bearer {surgeon_token}"}
    r = client.post("/api/auth/refresh", headers=h)
    assert r.status_code == 200
    new_tok = r.json()["access_token"]
    # new token works
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_tok}"}).status_code == 200
    # refresh without auth -> 401
    assert client.post("/api/auth/refresh").status_code == 401


def test_analyze_async_job(client, surgeon_token):
    procs = client.get("/api/procedures").json()["items"]
    pid = procs[0]["id"]
    h = {"Authorization": f"Bearer {surgeon_token}"}
    r = client.post(f"/api/procedures/{pid}/analyze", headers=h).json()
    assert "job_id" in r
    job = client.get(f"/api/jobs/{r['job_id']}").json()
    # background task runs inside TestClient request lifecycle -> done by now
    assert job["status"] in ("running", "done", "queued")
