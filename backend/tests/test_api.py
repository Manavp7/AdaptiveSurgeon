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
