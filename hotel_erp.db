from datetime import datetime, timedelta
import pandas as pd


def init_approval_schema(conn_factory):
    with conn_factory() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS approval_requests(
            request_id TEXT PRIMARY KEY,
            module TEXT,
            record_id TEXT,
            workflow_id TEXT,
            title TEXT,
            submitted_by TEXT,
            submitted_username TEXT,
            submitted_at TEXT,
            current_level INTEGER,
            total_levels INTEGER,
            status TEXT,
            priority TEXT,
            due_at TEXT,
            escalated INTEGER DEFAULT 0,
            escalated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS approval_steps(
            step_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            level_no INTEGER,
            approver_role TEXT,
            approver_username TEXT,
            status TEXT,
            acted_by TEXT,
            acted_username TEXT,
            acted_at TEXT,
            decision TEXT,
            comments TEXT,
            FOREIGN KEY(request_id) REFERENCES approval_requests(request_id)
        );
        """)
        c.commit()


def approval_chain_for_value(value):
    value = abs(float(value or 0))
    if value <= 5000:
        return ["Manager"]
    if value <= 25000:
        return ["Manager", "Accounts"]
    return ["Manager", "Accounts", "Admin"]


def submit_request(execute, scalar, module, record_id, title, submitted_by,
                   submitted_username, approver_chain, sla_hours=24):
    now = datetime.now().isoformat(timespec="seconds")
    due = (datetime.now() + timedelta(hours=sla_hours)).isoformat(timespec="seconds")
    n = int(scalar("SELECT COUNT(*) FROM approval_requests", default=0)) + 1
    request_id = f"APR-{n:06d}"
    execute("""INSERT INTO approval_requests(
        request_id,module,record_id,workflow_id,title,submitted_by,submitted_username,
        submitted_at,current_level,total_levels,status,priority,due_at,escalated,escalated_at
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        request_id,module,record_id,"",title,submitted_by,submitted_username,
        now,1,len(approver_chain),"Pending","Normal",due,0,""
    ))
    for level_no, role in enumerate(approver_chain, start=1):
        execute("""INSERT INTO approval_steps(
            request_id,level_no,approver_role,approver_username,status,acted_by,acted_username,
            acted_at,decision,comments
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""", (
            request_id,level_no,role,"","Pending","","","","",""
        ))
    return request_id


def is_step_pending(query, step_id):
    df=query("SELECT status FROM approval_steps WHERE step_id=?",(step_id,))
    return (not df.empty) and str(df.iloc[0]["status"])=="Pending"


def act_on_step_conn(c, request_id, step_id, decision, comments, acted_by, acted_username):
    now=datetime.now().isoformat(timespec="seconds")
    step_status={"Approve":"Approved","Reject":"Rejected","Return":"Returned"}[decision]
    cur=c.execute("""UPDATE approval_steps SET status=?,acted_by=?,acted_username=?,acted_at=?,decision=?,comments=?
                     WHERE step_id=? AND status='Pending'""",
                  (step_status,acted_by,acted_username,now,decision,comments,step_id))
    if cur.rowcount!=1:
        raise RuntimeError("This request was already processed by another approver.")
    if decision=="Reject":
        c.execute("UPDATE approval_requests SET status='Rejected' WHERE request_id=?",(request_id,))
        return "rejected"
    if decision=="Return":
        c.execute("UPDATE approval_requests SET status='Returned for Correction' WHERE request_id=?",(request_id,))
        return "returned"
    row=c.execute("SELECT current_level,total_levels FROM approval_requests WHERE request_id=?",(request_id,)).fetchone()
    if not row:
        raise RuntimeError("Approval request no longer exists.")
    current_level,total_levels=int(row[0]),int(row[1])
    if current_level>=total_levels:
        c.execute("UPDATE approval_requests SET status='Approved' WHERE request_id=?",(request_id,))
        return "final_approved"
    c.execute("UPDATE approval_requests SET current_level=current_level+1 WHERE request_id=?",(request_id,))
    return "next_level"


def _empty_or_query(query, sql, params=()):
    try:
        return query(sql,params)
    except Exception:
        return pd.DataFrame()


def get_inbox(query, username, role):
    return _empty_or_query(query,"""
        SELECT ar.*, s.step_id, s.level_no, s.approver_role, s.approver_username,
               s.status AS step_status
        FROM approval_requests ar
        JOIN approval_steps s ON s.request_id=ar.request_id AND s.level_no=ar.current_level
        WHERE ar.status='Pending' AND s.status='Pending'
          AND ar.submitted_username<>?
          AND (s.approver_username=? OR (COALESCE(s.approver_username,'')='' AND s.approver_role=?) OR ?='Admin')
        ORDER BY ar.due_at, ar.request_id
    """,(username,username,role,role))


def get_pending(query):
    return _empty_or_query(query,"SELECT * FROM approval_requests WHERE status='Pending' ORDER BY due_at")


def get_my_requests(query, username):
    return _empty_or_query(query,"SELECT * FROM approval_requests WHERE submitted_username=? ORDER BY submitted_at DESC",(username,))


def get_history(query):
    return _empty_or_query(query,"""
        SELECT ar.request_id,ar.module,ar.record_id,ar.title,ar.submitted_by,ar.submitted_at,
               ar.status,ar.current_level,ar.total_levels,s.level_no,s.approver_role,s.status AS step_status,
               s.acted_by,s.acted_at,s.decision,s.comments
        FROM approval_requests ar LEFT JOIN approval_steps s ON s.request_id=ar.request_id
        ORDER BY ar.submitted_at DESC,s.level_no
    """)
