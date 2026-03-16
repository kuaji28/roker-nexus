"""
push_supabase.py — Roker Nexus Batch Pusher
============================================
Pushes all remaining data batches to Supabase.
Run this from Windows once (double-click or python push_supabase.py).

Requirements:  pip install requests
Place this file next to the batch_files/ folder.

Tables covered:
  precios        → pr_0000.js .. pr_0044.js
  ventas         → vn_0000.js .. vn_0030.js
  stock_snapshots→ ss_p0000.js .. ss_p0019.js  (SJ snapshots)
  stock_snapshots→ ss_r0000.js .. ss_r0191.js  (rest — lower priority)

Already pushed (skip automatically via upsert):
  pr_0000–pr_0004, pr_0013, pr_0014, pr_0029, pr_0030
  vn_0000, ss_p0000

The upsert header (resolution=merge-duplicates) makes re-runs safe.
"""

import re, json, pathlib, time, sys
try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run:  pip install requests")
    input("Press Enter to exit...")
    sys.exit(1)

# ── Supabase config ─────────────────────────────────────────────────────────
SUPABASE_URL = "https://zjrabazzvckvxhufppoa.supabase.co/rest/v1"
SERVICE_KEY  = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqcmFiYXp6dmNrdnhodWZwcG9hIiwicm9sZSI"
    "6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQxNjc5NSwiZXhwIjoyMDg4OTkyNzk1fQ"
    ".pi7WKHKiU-lw_aMJoHbRWNIszLKUxnz2GIIaYeFVgCU"
)
HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal,resolution=merge-duplicates",
}

# ── Batch order (table, filename prefix, count) ──────────────────────────────
BATCHES = [
    # precios — fill in the gaps and re-run missing ones (upsert is safe)
    *[("precios",         f"pr_{i:04d}.js") for i in range(45)],
    # ventas
    *[("ventas",          f"vn_{i:04d}.js") for i in range(31)],
    # stock_snapshots SJ
    *[("stock_snapshots", f"ss_p{i:04d}.js") for i in range(20)],
    # stock_snapshots rest (lower priority — comment out if not needed yet)
    *[("stock_snapshots", f"ss_r{i:04d}.js") for i in range(192)],
]

BATCH_DIR = pathlib.Path(__file__).parent / "batch_files"

# ── on_conflict params per table (matches UNIQUE constraint, NOT the PK) ─────
ON_CONFLICT = {
    "precios":         "codigo,fecha",
    "ventas":          "codigo,fecha_desde,fecha_hasta",
    "stock_snapshots": "codigo,deposito,fecha",
}

# ── JSON extractor ────────────────────────────────────────────────────────────
_JSON_ARRAY_RE = re.compile(r"body:JSON\.stringify\((\[.*\])\)", re.DOTALL)

def extract_rows(js_text: str) -> list:
    m = _JSON_ARRAY_RE.search(js_text)
    if not m:
        raise ValueError("Could not find JSON array in file")
    return json.loads(m.group(1))

# ── Push one batch ────────────────────────────────────────────────────────────
def push_batch(table: str, filename: str) -> dict:
    fpath = BATCH_DIR / filename
    if not fpath.exists():
        return {"skip": True, "reason": "file not found"}

    rows = extract_rows(fpath.read_text(encoding="utf-8"))

    conflict_cols = ON_CONFLICT.get(table, "")
    url = (f"{SUPABASE_URL}/{table}?on_conflict={conflict_cols}"
           if conflict_cols else f"{SUPABASE_URL}/{table}")

    resp = requests.post(url, headers=HEADERS, json=rows, timeout=60)
    ok = resp.status_code in (200, 201)
    result = {"ok": ok, "status": resp.status_code, "n": len(rows)}
    if not ok:
        result["error_body"] = resp.text[:500]   # primeros 500 chars del error
    return result

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Roker Nexus — Supabase Batch Pusher")
    print(f"Batch dir: {BATCH_DIR}")
    print(f"Total batches: {len(BATCHES)}\n")

    ok_count = err_count = skip_count = 0
    errors = []

    for i, (table, fname) in enumerate(BATCHES, 1):
        result = push_batch(table, fname)

        if result.get("skip"):
            skip_count += 1
            print(f"[{i:>3}/{len(BATCHES)}] SKIP  {fname}  ({result['reason']})")
            continue

        status_icon = "✓" if result["ok"] else "✗"
        print(f"[{i:>3}/{len(BATCHES)}] {status_icon}  {fname}  → {table}  "
              f"status={result['status']}  rows={result['n']}")

        if result["ok"]:
            ok_count += 1
        else:
            err_count += 1
            errors.append((fname, result["status"]))
            if result.get("error_body"):
                print(f"         ERROR: {result['error_body']}")

        # Tiny delay to avoid hammering the API
        time.sleep(0.15)

    print(f"\n{'='*60}")
    print(f"Done.  OK={ok_count}  ERRORS={err_count}  SKIPPED={skip_count}")
    if errors:
        print("\nFailed batches:")
        for fname, status in errors:
            print(f"  {fname}  HTTP {status}")

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
