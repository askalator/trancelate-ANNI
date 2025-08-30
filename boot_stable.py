#!/usr/bin/env python3
"""
Boot orchestrator for a stable local run of TranceLate (mt_server + mt_guard).
- Stops any running stack (via stop_local.sh if present)
- Starts the stack (start_local.sh)
- Waits for /health
- Binds provider via /admin/reload until /meta shows provider_configured:true
- Runs two smoke tests: plain MT and PH-only (no HTML), prints a compact summary
Run from project root: .venv/bin/python boot_stable.py
"""
from __future__ import annotations
import json, os, sys, time, subprocess, urllib.request, urllib.error

BASE = os.environ.get("TL_BASE", "http://127.0.0.1:8091")
HEALTH = f"{BASE}/health"
META = f"{BASE}/meta"
RELOAD = f"{BASE}/admin/reload"
TRANSLATE = f"{BASE}/translate"


def http_json(method: str, url: str, data: dict | None = None, timeout: float = 10.0):
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    else:
        body = None
    with urllib.request.urlopen(req, body, timeout=timeout) as r:  # type: ignore[arg-type]
        ct = r.headers.get("content-type", "")
        raw = r.read()
        if "application/json" in ct:
            return json.loads(raw.decode("utf-8"))
        return raw.decode("utf-8")


def stop_stack():
    if os.path.exists("./stop_local.sh"):
        subprocess.run(["bash", "./stop_local.sh"], check=False)


def start_stack():
    if not os.path.exists("./start_local.sh"):
        print("❌ start_local.sh nicht gefunden. Bitte im Projekt-Root ausführen.")
        sys.exit(1)
    # Start in background; script selbst blockiert ggf. — wir warten per health
    subprocess.Popen(["bash", "./start_local.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_health(timeout_s: int = 60) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            j = http_json("GET", HEALTH, None, timeout=3)
            if isinstance(j, dict) and j.get("ok") is True:
                print("🟢 Guard /health OK")
                return
        except Exception:
            pass
        time.sleep(1)
    print("❌ Guard /health blieb down")
    sys.exit(1)


def bind_provider(timeout_s: int = 60) -> None:
    t0 = time.time()
    last_meta = None
    while time.time() - t0 < timeout_s:
        try:
            http_json("POST", RELOAD, {})
            m = http_json("GET", META, None)
            last_meta = m
            if isinstance(m, dict) and m.get("provider_configured") is True:
                print("🟢 Provider gebunden")
                return
        except Exception:
            pass
        time.sleep(1)
    print("❌ Provider nicht gebunden. Letzte /meta:", last_meta)
    sys.exit(1)


def smoke(text: str):
    payload = {"source": "de", "target": "en", "text": text}
    j = http_json("POST", TRANSLATE, payload, timeout=15)
    if not isinstance(j, dict):
        print("❌ Unerwartete Antwort:", j)
        sys.exit(1)
    tr = j.get("translated_text")
    prov = j.get("provenance", {})
    checks = j.get("checks", {})
    print(json.dumps(j, ensure_ascii=False))
    ok = bool(checks.get("ok"))
    engine = prov.get("engine")
    return ok, engine, checks


def main():
    print("🛑 Stoppe laufenden Stack (falls vorhanden)…")
    stop_stack()
    print("▶️  Starte Stack…")
    start_stack()
    print("⏳ Warte auf /health…")
    wait_health()
    print("🔁 Binde Provider…")
    bind_provider()
    print("— Smoke A: Basis —")
    ok1, eng1, _ = smoke("Guten Morgen")
    if eng1 != "self_host_mt":
        print("❌ Engine ist nicht self_host_mt — aktueller Wert:", eng1)
        sys.exit(1)
    if not ok1:
        print("❌ Checks fehlgeschlagen bei Smoke A")
        sys.exit(1)
    print("— Smoke B: Platzhalter —")
    ok2, _, checks2 = smoke("Nur heute: {{COUNT}} Plätze frei bei {app}!")
    if not ok2 or not (checks2.get("ph_ok") and checks2.get("num_ok")):
        print("❌ Platzhalter-/Zahl-Check fehlgeschlagen")
        sys.exit(1)
    print("✅ STABIL: Stack läuft, Provider gebunden, Qualität (PH/Zahl) grün")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(130)



