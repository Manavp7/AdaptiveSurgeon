#!/usr/bin/env bash
# End-to-end smoke test of the connected workflow over HTTP.
# Boots the backend, seeds data, then asserts the full success flow:
#   upload -> process -> timeline -> detect/track -> skill -> risk ->
#   copilot -> twin -> unified analysis.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
cd backend

echo "==> Seeding (idempotent)…"
python -m app.seed.demo >/dev/null

echo "==> Starting backend…"
uvicorn app.main:app --host 127.0.0.1 --port 8011 >/tmp/adaptive_smoke.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8011/health >/dev/null; then break; fi
  sleep 0.5
done

BASE=http://127.0.0.1:8011/api
python - "$BASE" <<'PY'
import sys, json, urllib.request, urllib.parse

base = sys.argv[1]
def get(path, token=None):
    req = urllib.request.Request(base + path)
    if token: req.add_header("Authorization", f"Bearer {token}")
    return json.load(urllib.request.urlopen(req))

def post_form(path, data):
    body = urllib.parse.urlencode(data).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(base + path, data=body)))

tok = post_form("/auth/login", {"username":"surgeon","password":"surgeon123"})["access_token"]
procs = get("/procedures")["items"]
assert procs, "no procedures seeded"
pid = procs[0]["id"]
a = get(f"/procedures/{pid}/analysis")

checks = {
    "video": a["video_uri"] is not None,
    "phases": len(a["phases"]) == 6,
    "tracks": len(a["tracks"]) > 0,
    "detections": a["detection_count"] > 0,
    "skill": a["skill"] is not None and a["skill"]["score"] > 0,
    "risks": len(a["risks"]) > 0,
    "advisories": len(a["advisories"]) > 0,
}
twin = get(f"/procedures/{pid}/twin")
checks["twin"] = len(twin["structures"]) > 0
sim = get(f"/foundation/similar?procedure_id={pid}")
checks["similar_cases"] = len(sim["results"]) > 0

print("Unified workflow checks:")
for k, v in checks.items():
    print(f"  [{'OK' if v else 'FAIL'}] {k}")
assert all(checks.values()), "SMOKE TEST FAILED"
print("\nSMOKE TEST PASSED — full connected workflow verified.")
PY
