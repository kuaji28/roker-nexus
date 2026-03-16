#!/usr/bin/env python3
"""
push_to_supabase.py — Roker Nexus
Empuja todos los datos de SQLite a Supabase.
Ejecutar desde tu computadora (no desde el VM):
    pip install requests
    python push_to_supabase.py
"""
import sqlite3
import json
import sys
import os
import time
import requests
from datetime import datetime

# ── Configuración ───────────────────────────────────────────────────────────
SUPABASE_URL = "https://zjrabazzvckvxhufppoa.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqcmFiYXp6dmNrdnhodWZwcG9hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQxNjc5NSwiZXhwIjoyMDg4OTkyNzk1fQ.pi7WKHKiU-lw_aMJoHbRWNIszLKUxnz2GIIaYeFVgCU"
DB_PATH = os.path.join(os.path.dirname(__file__), "roker_nexus.db")
BATCH_SIZE = 200
DELAY_BETWEEN_BATCHES = 0.1   # segundos entre batches
DELAY_ON_ERROR = 2.0          # segundos si hay error

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal,resolution=merge-duplicates",
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def post_batch(table: str, rows: list, prefer: str = None) -> tuple[bool, str]:
    headers = {**HEADERS}
    if prefer:
        headers["Prefer"] = prefer
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers,
            data=json.dumps(rows),
            timeout=30,
        )
        if r.status_code <= 201:
            return True, ""
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)


def push_table(conn, table: str, query: str, transform=None, conflict="merge"):
    """
    Pushes all rows from `query` to Supabase table in batches.
    transform: optional function to convert a Row to a dict
    conflict: 'merge' or 'ignore'
    """
    prefer = "return=minimal,resolution=merge-duplicates" if conflict == "merge" else "return=minimal"
    cur = conn.execute(query)
    rows = cur.fetchall()
    total = len(rows)
    if total == 0:
        print(f"  {table}: 0 rows — skip")
        return 0, 0

    ok_total, fail_total = 0, 0
    for i in range(0, total, BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        if transform:
            batch = [transform(r) for r in chunk]
        else:
            batch = [dict(r) for r in chunk]

        ok, err = post_batch(table, batch, prefer=prefer)
        if ok:
            ok_total += len(chunk)
        else:
            fail_total += len(chunk)
            print(f"  ⚠ {table} batch {i//BATCH_SIZE}: {err}")
            time.sleep(DELAY_ON_ERROR)

        pct = int((i + len(chunk)) / total * 100)
        print(f"  {table}: {i + len(chunk)}/{total} ({pct}%) — ok={ok_total} fail={fail_total}", end="\r")

        if DELAY_BETWEEN_BATCHES > 0:
            time.sleep(DELAY_BETWEEN_BATCHES)

    print(f"  {table}: {total} rows — ✅ {ok_total} ok / ❌ {fail_total} fail          ")
    return ok_total, fail_total


# ── Transformaciones por tabla ────────────────────────────────────────────────
def transform_articulos(r):
    return {
        "codigo": r["codigo"],
        "descripcion": r["descripcion"],
        "tipo_codigo": r["tipo_codigo"],
        "marca": r["marca"],
        "rubro": r["rubro"],
        "en_lista_negra": bool(r["en_lista_negra"]),
        "creado_en": r["creado_en"],
        "actualizado_en": r["actualizado_en"],
    }


def transform_precios(r):
    return {
        "codigo": r["codigo"],
        "lista_1": r["lista_1"],
        "lista_2": r["lista_2"],
        "lista_3": r["lista_3"],
        "lista_4": r["lista_4"],
        "lista_5": r["lista_5"],
        "moneda": r["moneda"],
        "fecha": r["fecha"],
        "importado_en": r["importado_en"],
    }


def transform_ventas(r):
    return {
        "codigo": r["codigo"],
        "descripcion": r["descripcion"],
        "cantidad": r["cantidad"],
        "total_venta_ars": r["total_venta_ars"],
        "marca": r["marca"],
        "fecha_desde": r["fecha_desde"],
        "fecha_hasta": r["fecha_hasta"],
        "importado_en": r["importado_en"],
    }


def transform_stock(r):
    return {
        "codigo": r["codigo"],
        "deposito": r["deposito"],
        "descripcion": r["descripcion"],
        "rubro": r["rubro"],
        "stock": r["stock"],
        "stock_minimo": r["stock_minimo"],
        "stock_optimo": r["stock_optimo"],
        "stock_maximo": r["stock_maximo"],
        "fecha": r["fecha"],
        "fecha_snapshot": r["fecha_snapshot"],
        "importado_en": r["importado_en"],
    }


def transform_remitos(r):
    return {
        "numero": r["numero"],
        "fecha": r["fecha"],
        "origen": r["deposito_origen"],
        "destino": r["deposito_destino"],
        "articulos_count": None,
        "importado_en": r["importado_en"],
    }


def transform_config(r):
    return {
        "clave": r["clave"],
        "valor": r["valor"],
        "descripcion": r["descripcion"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def check_current_counts():
    """Check current row counts in Supabase"""
    tables = ["configuracion", "articulos", "precios", "stock_snapshots", "ventas", "remitos_internos"]
    print("\n📊 Current Supabase counts:")
    for t in tables:
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/{t}?select=*&limit=1",
                headers={**HEADERS, "Prefer": "count=exact"},
                timeout=10,
            )
            cr = r.headers.get("content-range", "?")
            total = cr.split("/")[-1] if "/" in cr else "?"
            print(f"  {t:25s}: {total:>8} rows")
        except Exception as e:
            print(f"  {t:25s}: ERROR {e}")
    print()


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found: {DB_PATH}")
        print("   Run from the roker_nexus directory or adjust DB_PATH")
        sys.exit(1)

    print(f"🚀 Roker Nexus — Supabase Pusher")
    print(f"   DB: {DB_PATH}")
    print(f"   Target: {SUPABASE_URL}")
    print(f"   Batch size: {BATCH_SIZE} rows\n")

    check_current_counts()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    start = time.time()

    # ── 1. Configuracion ──────────────────────────────────────────────────────
    print("1️⃣  configuracion...")
    push_table(
        conn, "configuracion",
        "SELECT clave, valor, descripcion FROM configuracion",
        transform=transform_config,
        conflict="ignore",
    )

    # ── 2. Articulos ──────────────────────────────────────────────────────────
    print("2️⃣  articulos...")
    push_table(
        conn, "articulos",
        "SELECT codigo,descripcion,tipo_codigo,marca,rubro,en_lista_negra,creado_en,actualizado_en FROM articulos",
        transform=transform_articulos,
        conflict="merge",
    )

    # ── 3. Precios ────────────────────────────────────────────────────────────
    print("3️⃣  precios...")
    push_table(
        conn, "precios",
        "SELECT codigo,lista_1,lista_2,lista_3,lista_4,lista_5,moneda,fecha,importado_en FROM precios",
        transform=transform_precios,
        conflict="ignore",
    )

    # ── 4. Ventas ─────────────────────────────────────────────────────────────
    print("4️⃣  ventas...")
    push_table(
        conn, "ventas",
        "SELECT codigo,descripcion,cantidad,total_venta_ars,marca,fecha_desde,fecha_hasta,importado_en FROM ventas",
        transform=transform_ventas,
        conflict="ignore",
    )

    # ── 5. Stock Snapshots ────────────────────────────────────────────────────
    print("5️⃣  stock_snapshots...")
    push_table(
        conn, "stock_snapshots",
        "SELECT codigo,deposito,descripcion,rubro,stock,stock_minimo,stock_optimo,stock_maximo,fecha,fecha_snapshot,importado_en FROM stock_snapshots",
        transform=transform_stock,
        conflict="ignore",
    )

    # ── 6. Remitos Internos ───────────────────────────────────────────────────
    print("6️⃣  remitos_internos...")
    push_table(
        conn, "remitos_internos",
        "SELECT numero,fecha,deposito_origen,deposito_destino,importado_en FROM remitos_internos",
        transform=transform_remitos,
        conflict="ignore",
    )

    conn.close()

    elapsed = time.time() - start
    print(f"\n✅ Terminado en {elapsed:.0f}s")
    check_current_counts()


if __name__ == "__main__":
    # Parse simple flags
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    main()
