"""Approval workflow engine for Hotel Control Tower Enterprise."""
from __future__ import annotations

from datetime import datetime, timedelta
import pandas as pd


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_approval_schema(conn_factory) -> None:
    with conn_factory() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS approval_requests(
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            record_id TEXT NOT NULL,
            title TEXT NOT NULL,
            submitted_by TEXT,
            submitted_username TEXT,
            submitted_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            current_level INTEGER NOT NULL DEFAULT 1,
            total_levels INTEGER NOT NULL DEFAULT 1,
            sla_due_at TEXT,
            final_action_by TEXT,
            final_action_at TEXT,
            final_comments TEXT
        );
        CREATE TABLE IF NOT EXISTS approval_steps(
            step_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            level_no INTEGER NOT NULL,
            approver_role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            acted_by TEXT,
            acted_username TEXT,
            acted_at TEXT,
            comments TEXT,
            FOREIGN KEY(request_id) REFERENCES approval_requests(request_id)
        );
        CREATE TABLE IF NOT EXISTS approval_history(
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            step_id INTEGER,
            action TEXT NOT NULL,
            action_by TEXT,
            action_username TEXT,
            comments TEXT,
            action_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_approval_request_status ON approval_requests(status);
        CREATE INDEX IF NOT EXISTS idx_approval_step_queue ON approval_steps(status, approver_role);
        """)
        c.commit()


def approval_chain_for_value(value: float) -> list[str]:
    value = abs(float(value or 0))
    if value <= 5_000:
        return ["Manager"]
    if value <= 25_000:
        return ["Manager", "Accounts"]
    return ["Manager", "Accounts", "Admin"]


def submit_request(execute, scalar, *, module: str, record_id: str, title: str,
                   submitted_by: str, submitted_username: str,
                   approver_chain: list[str], sla_hours: int = 24) -> int:
    chain = approver_chain or ["Manager"]
    submitted_at = _now()
    due = (datetime.now() + timedelta(hours=int(sla_hours or 24))).isoformat(timespec="seconds")
    execute("""INSERT INTO approval_requests(
        module,record_id,title,submitted_by,submitted_username,submitted_at,status,
        current_level,total_levels,sla_due_at
    ) VALUES(?,?,?,?,?,?,'Pending',1,?,?)""",
    (module, record_id, title, submitted_by, submitted_username, submitted_at, len(chain), due))
    request_id = int(scalar("SELECT MAX(request_id) FROM approval_requests", default=0))
    for level, role in enumerate(chain, start=1):
        status = "Pending" if level == 1 else "Waiting"
        execute("""INSERT INTO approval_steps(request_id,level_no,approver_role,status)
                   VALUES(?,?,?,?)""", (request_id, level, role, status))
    return request_id


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def get_inbox(query, username: str, role: str) -> pd.DataFrame:
    sql = """
    SELECT r.request_id,r.module,r.record_id,r.title,r.submitted_by,r.submitted_username,
           r.submitted_at,r.status,r.current_level,r.total_levels,r.sla_due_at,
           s.step_id,s.level_no,s.approver_role,s.status AS step_status
    FROM approval_requests r
    JOIN approval_steps s ON s.request_id=r.request_id
    WHERE r.status='Pending' AND s.status='Pending'
      AND (s.approver_role=? OR ?='Admin')
      AND COALESCE(r.submitted_username,'')<>?
    ORDER BY r.submitted_at
    """
    return query(sql, (role, role, username))


def get_pending(query) -> pd.DataFrame:
    return query("""SELECT request_id,module,record_id,title,submitted_by,submitted_at,
                           current_level,total_levels,sla_due_at,status
                    FROM approval_requests WHERE status='Pending'
                    ORDER BY submitted_at""")


def get_my_requests(query, username: str) -> pd.DataFrame:
    return query("""SELECT request_id,module,record_id,title,submitted_at,status,
                           current_level,total_levels,final_action_by,final_action_at,final_comments
                    FROM approval_requests WHERE submitted_username=?
                    ORDER BY submitted_at DESC""", (username,))


def get_history(query) -> pd.DataFrame:
    return query("""SELECT h.history_id,h.request_id,r.module,r.record_id,r.title,
                           h.action,h.action_by,h.comments,h.action_at
                    FROM approval_history h
                    LEFT JOIN approval_requests r ON r.request_id=h.request_id
                    ORDER BY h.action_at DESC""")


def is_step_pending(query, step_id: int) -> bool:
    df = query("SELECT status FROM approval_steps WHERE step_id=?", (int(step_id),))
    return not df.empty and str(df.iloc[0]["status"]) == "Pending"


def act_on_step_conn(c, request_id: int, step_id: int, decision: str,
                     comments: str, actor_name: str, actor_username: str) -> str:
    decision_norm = str(decision).strip().lower()
    if decision_norm not in {"approve", "reject", "return"}:
        raise ValueError("Decision must be Approve, Reject, or Return.")

    step = c.execute("""SELECT level_no,status FROM approval_steps
                        WHERE step_id=? AND request_id=?""",
                     (int(step_id), int(request_id))).fetchone()
    if not step or step[1] != "Pending":
        raise RuntimeError("Approval step is no longer pending.")

    now = _now()
    if decision_norm == "approve":
        c.execute("""UPDATE approval_steps SET status='Approved',acted_by=?,acted_username=?,
                     acted_at=?,comments=? WHERE step_id=?""",
                  (actor_name, actor_username, now, comments, int(step_id)))
        c.execute("""INSERT INTO approval_history(request_id,step_id,action,action_by,
                     action_username,comments,action_at) VALUES(?,?,?,?,?,?,?)""",
                  (int(request_id), int(step_id), "Approved", actor_name, actor_username, comments, now))
        next_step = c.execute("""SELECT step_id,level_no FROM approval_steps
                                 WHERE request_id=? AND status='Waiting'
                                 ORDER BY level_no LIMIT 1""", (int(request_id),)).fetchone()
        if next_step:
            c.execute("UPDATE approval_steps SET status='Pending' WHERE step_id=?", (next_step[0],))
            c.execute("UPDATE approval_requests SET current_level=? WHERE request_id=?",
                      (next_step[1], int(request_id)))
            return "next_level"
        c.execute("""UPDATE approval_requests SET status='Approved',final_action_by=?,
                     final_action_at=?,final_comments=? WHERE request_id=?""",
                  (actor_name, now, comments, int(request_id)))
        return "final_approved"

    final_status = "Rejected" if decision_norm == "reject" else "Returned"
    c.execute("""UPDATE approval_steps SET status=?,acted_by=?,acted_username=?,acted_at=?,comments=?
                 WHERE step_id=?""", (final_status, actor_name, actor_username, now, comments, int(step_id)))
    c.execute("UPDATE approval_steps SET status='Cancelled' WHERE request_id=? AND status='Waiting'",
              (int(request_id),))
    c.execute("""UPDATE approval_requests SET status=?,final_action_by=?,final_action_at=?,
                 final_comments=? WHERE request_id=?""",
              (final_status, actor_name, now, comments, int(request_id)))
    c.execute("""INSERT INTO approval_history(request_id,step_id,action,action_by,
                 action_username,comments,action_at) VALUES(?,?,?,?,?,?,?)""",
              (int(request_id), int(step_id), final_status, actor_name, actor_username, comments, now))
    return "rejected" if decision_norm == "reject" else "returned"
