"""
RetailRecon V28 - Reconciliation Run History.

Additive, standalone persistence for reconciliation runs. Does not modify
core.py, db.py, or any existing reconciliation logic - it only reads the
already-built st.session_state.ct_result dict and stores/retrieves full
snapshots of it, keyed by a generated Run ID (RUN-YYYYMMDD-NNN).

STORAGE CAVEAT - read before treating this as audit-proof:
This ships with a local SQLite file as its default backend so it is fully
self-contained and testable today, with zero dependency on files not yet
available in this engagement. On some hosting setups (notably Streamlit
Community Cloud) local filesystem writes are NOT guaranteed to survive an
app restart/redeploy - only the *live* filesystem is guaranteed for the life
of the running container. Your existing db.py evidently already solves
durable storage for other data (masters, corrections, JV approvals, GL
config) in your real deployment environment, which strongly implies it is
already backed by something that survives restarts there. db.py has never
been sent in this engagement, so this module could not be built against its
real schema/engine.

To close this gap once db.py is available: replace _connect() below with
whatever connection db.py already uses (or point RUN_HISTORY_DB_PATH at
wherever db.py's own SQLite file already lives, if that's what it uses), so
Run History gets the identical durability guarantee the rest of the app's
persistent data already has. Everything else in this module (the run_id
scheme, save/list/load functions, the page that uses them) is
backend-agnostic and does not need to change.
"""
from __future__ import annotations
import os
import re
import pickle
import sqlite3
import pandas as pd

RUN_HISTORY_DB_PATH = os.environ.get("RETAILRECON_RUN_HISTORY_DB", "data/run_history.db")

# Every key here that exists in st.session_state.ct_result gets snapshotted.
# Keys not present for a given run are simply skipped - additive, no schema
# migration needed when a future version adds a new dataset to ct_result.
DATASET_KEYS = [
    "matched", "unmatched_sales", "unmatched_pos", "carry_forward", "cash_transactions",
    "tender", "sales_details", "store613_bridge", "pos", "bank", "quarantine",
    "settlement_batches", "settlement_bank_unmatched", "provider_payout_batches",
    "settlement_blocker_summary",
]


def _connect():
    d = os.path.dirname(RUN_HISTORY_DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(RUN_HISTORY_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            username TEXT,
            user_name TEXT,
            period_from TEXT,
            period_to TEXT,
            matched_count INTEGER,
            unmatched_sales_count INTEGER,
            unmatched_pos_count INTEGER,
            bank_settled_count INTEGER,
            note TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_data (
            run_id TEXT NOT NULL,
            dataset TEXT NOT NULL,
            payload BLOB,
            PRIMARY KEY (run_id, dataset)
        )
    """)
    return conn


def init_run_history_db():
    _connect().close()


def generate_run_id(today_str):
    """
    today_str: an already-computed 'YYYYMMDD' string. This module never calls
    time functions itself (matching this codebase's testing conventions
    elsewhere) - the caller (a Streamlit page, which legitimately needs real
    wall-clock time) supplies it, so this stays trivially unit-testable.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT run_id FROM runs WHERE run_id LIKE ? ORDER BY run_id DESC LIMIT 1",
            (f"RUN-{today_str}-%",),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        seq = 1
    else:
        m = re.search(r"-(\d+)$", rows[0][0])
        seq = int(m.group(1)) + 1 if m else 1
    return f"RUN-{today_str}-{seq:03d}"


def save_run(run_id, ct_result, created_at, username="", user_name="",
             period_from="", period_to="", note=""):
    """
    Persists a full snapshot of ct_result under run_id.

    Safe to call more than once with the SAME run_id - e.g. Settlement Batch
    Engine or JV Creation refining the same run's matched/settlement data
    later in the same working session. Each call overwrites *that run's*
    stored datasets with the latest state, so a run always reflects "what
    this reconciliation looks like right now" - it never touches any other
    run_id's stored data. A distinct, permanently separate audit snapshot is
    only created by calling generate_run_id() for a brand new run_id, which
    is what "RUN RECONCILIATION" does each time it succeeds.
    """
    if ct_result is None:
        return
    matched = ct_result.get("matched")
    matched_count = int(len(matched)) if matched is not None else 0
    bank_settled_count = (
        int(matched["Bank Settled"].sum())
        if matched is not None and not matched.empty and "Bank Settled" in matched.columns
        else 0
    )
    us = ct_result.get("unmatched_sales")
    up = ct_result.get("unmatched_pos")

    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO runs (run_id, created_at, username, user_name, period_from, period_to,
                               matched_count, unmatched_sales_count, unmatched_pos_count,
                               bank_settled_count, note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(run_id) DO UPDATE SET
                username=excluded.username, user_name=excluded.user_name,
                period_from=excluded.period_from, period_to=excluded.period_to,
                matched_count=excluded.matched_count,
                unmatched_sales_count=excluded.unmatched_sales_count,
                unmatched_pos_count=excluded.unmatched_pos_count,
                bank_settled_count=excluded.bank_settled_count,
                note=excluded.note
        """, (
            run_id, created_at, username, user_name, period_from, period_to,
            matched_count,
            int(len(us)) if us is not None else 0,
            int(len(up)) if up is not None else 0,
            bank_settled_count, note,
        ))

        for key in DATASET_KEYS:
            val = ct_result.get(key)
            if val is None:
                continue
            blob = pickle.dumps(val)
            conn.execute("""
                INSERT INTO run_data (run_id, dataset, payload) VALUES (?,?,?)
                ON CONFLICT(run_id, dataset) DO UPDATE SET payload=excluded.payload
            """, (run_id, key, blob))
        conn.commit()
    finally:
        conn.close()


def list_runs(limit=200):
    """Most recent first. Returns an empty-but-correctly-shaped DataFrame if nothing saved yet."""
    conn = _connect()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", conn, params=(limit,)
        )
    finally:
        conn.close()
    return df


def load_run(run_id):
    """Returns a ct_result-shaped dict reconstructed from storage. Empty dict if run_id unknown."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT dataset, payload FROM run_data WHERE run_id=?", (run_id,)
        ).fetchall()
    finally:
        conn.close()
    out = {}
    for dataset, payload in rows:
        try:
            out[dataset] = pickle.loads(payload)
        except Exception:
            out[dataset] = pd.DataFrame()
    return out


def get_run_meta(run_id):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        cols = [d[0] for d in conn.execute("SELECT * FROM runs LIMIT 0").description]
    finally:
        conn.close()
    return dict(zip(cols, row)) if row else {}


def delete_run(run_id):
    conn = _connect()
    try:
        conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM run_data WHERE run_id=?", (run_id,))
        conn.commit()
    finally:
        conn.close()


def engine_health():
    try:
        init_run_history_db()
        healthy = True
    except Exception:
        healthy = False
    return {
        "module": "run_history",
        "legacy_preserved": True,
        "extension_mode": "additive run persistence (SQLite-backed by default - see module docstring)",
        "storage_healthy": healthy,
    }
