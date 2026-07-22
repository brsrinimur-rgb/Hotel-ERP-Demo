import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import hmac
import os
import re
from datetime import datetime, date, timedelta
from io import BytesIO
from pathlib import Path

import approvals

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hotel_erp.db"

st.set_page_config(
    page_title="Hotel Control Tower Enterprise",
    page_icon="🏨",
    layout="wide"
)

# ---------------- Premium UI theme ----------------
st.markdown("""
<style>
:root {
    --erp-navy: #12213f;
    --erp-blue: #2563eb;
    --erp-cyan: #06b6d4;
    --erp-gold: #f59e0b;
    --erp-bg: #f5f7fb;
    --erp-card: #ffffff;
    --erp-text: #172033;
    --erp-muted: #64748b;
}

.stApp {
    background:
      radial-gradient(circle at 100% 0%, rgba(37,99,235,.08), transparent 24rem),
      linear-gradient(180deg, #f8fafc 0%, var(--erp-bg) 100%);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111d36 0%, #172b4d 55%, #0f3d56 100%);
    border-right: 1px solid rgba(255,255,255,.08);
}
[data-testid="stSidebar"] * { color: #f8fafc; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #dbeafe; }
[data-testid="stSidebar"] .stRadio label {
    border-radius: 10px;
    padding: .38rem .55rem;
    margin: .08rem 0;
    transition: all .18s ease;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,.10);
    transform: translateX(3px);
}
[data-testid="stSidebar"] .stButton button {
    width: 100%;
    background: rgba(255,255,255,.10);
    color: #fff;
    border: 1px solid rgba(255,255,255,.20);
}

h1, h2, h3 { color: var(--erp-navy); letter-spacing: -.02em; }
h1 {
    font-weight: 800 !important;
    padding-bottom: .45rem;
    border-bottom: 3px solid transparent;
    border-image: linear-gradient(90deg, var(--erp-blue), var(--erp-cyan), transparent) 1;
}

[data-testid="stForm"],
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,.96);
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.06);
}

/* Keep sidebar layout wrappers transparent.
   A global stVerticalBlockBorderWrapper rule creates a white panel inside
   the navy sidebar while sidebar text remains white, making it unreadable. */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #ffffff 0%, #f8fbff 100%);
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 1rem;
    box-shadow: 0 8px 22px rgba(37,99,235,.07);
}
[data-testid="stMetricValue"] { color: var(--erp-blue); font-weight: 800; }

.stButton > button, .stFormSubmitButton > button {
    border: 0 !important;
    border-radius: 10px !important;
    background: linear-gradient(90deg, var(--erp-blue), #3b82f6) !important;
    color: white !important;
    font-weight: 700 !important;
    box-shadow: 0 7px 16px rgba(37,99,235,.22);
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(37,99,235,.28);
}

[data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea {
    background: #f8fafc !important;
    border-color: #dbe3ef !important;
    border-radius: 10px !important;
}
[data-baseweb="input"] > div:focus-within, [data-baseweb="select"] > div:focus-within {
    border-color: var(--erp-blue) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
}

[data-testid="stDataFrame"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 8px 22px rgba(15,23,42,.05);
}

.stTabs [data-baseweb="tab-list"] {
    gap: .35rem;
    background: #eef4ff;
    padding: .35rem;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px;
    padding: .45rem .85rem;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: var(--erp-blue) !important;
    box-shadow: 0 4px 12px rgba(37,99,235,.12);
}

[data-testid="stAlert"] { border-radius: 12px; }
hr { border-color: #e2e8f0; }

/* Premium application shell */
.block-container { padding-top: 1.25rem; padding-bottom: 3rem; max-width: 1500px; }
[data-testid="stHeader"] { background: rgba(255,255,255,.72); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(226,232,240,.8); }
[data-testid="stToolbar"] { right: 1rem; }
.erp-brand-card { padding: 1rem 1rem .9rem; margin: .2rem 0 .9rem; border-radius: 18px; background: linear-gradient(135deg, rgba(59,130,246,.28), rgba(6,182,212,.12)); border: 1px solid rgba(255,255,255,.16); box-shadow: 0 12px 30px rgba(2,8,23,.20); }
.erp-brand-name { font-size: 1.35rem; font-weight: 850; color: #fff; letter-spacing: -.02em; }
.erp-brand-sub { color: #bfdbfe; font-size: .82rem; margin-top: .18rem; }
.erp-user-chip { margin: .4rem 0 1rem; padding: .7rem .8rem; border-radius: 13px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.10); }
[data-testid="stSidebar"] .stRadio > div { gap: .12rem; }
[data-testid="stSidebar"] .stRadio label { min-height: 2.45rem; border: 1px solid transparent; }
[data-testid="stSidebar"] .stRadio label:has(input:checked) { background: linear-gradient(90deg, rgba(59,130,246,.45), rgba(6,182,212,.22)); border-color: rgba(147,197,253,.35); box-shadow: 0 7px 18px rgba(2,8,23,.22); }
[data-testid="stSidebar"] .stRadio input { display: none; }
.main h1 { font-size: 2.35rem !important; margin-bottom: 1.2rem !important; }
[data-testid="stDownloadButton"] button { background: linear-gradient(90deg, #7c3aed, #2563eb) !important; min-height: 2.8rem; }
[data-testid="stMetric"] { position: relative; overflow: hidden; }
[data-testid="stMetric"]:before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 5px; background: linear-gradient(180deg, #2563eb, #06b6d4); }
.erp-hero { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1.1rem 1.25rem; margin: 0 0 1.1rem; border-radius: 18px; color: #fff; background: linear-gradient(120deg, #172554 0%, #1d4ed8 58%, #0891b2 100%); box-shadow: 0 18px 40px rgba(37,99,235,.18); }
.erp-hero-title { font-size: 1.15rem; font-weight: 800; }
.erp-hero-copy { color: #dbeafe; font-size: .88rem; margin-top: .15rem; }
.erp-live { padding: .35rem .65rem; border-radius: 999px; background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.2); white-space: nowrap; }

.dashboard-greeting { margin:.15rem 0 .3rem; color:#0f172a; font-size:1.05rem; font-weight:700; }
.dashboard-subcopy { color:#64748b; margin-bottom:1rem; }
.quick-action-label { color:#64748b; font-size:.78rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; margin:.4rem 0 .45rem; }
.alert-card { background:#fff; border:1px solid #e2e8f0; border-left:5px solid #f59e0b; border-radius:13px; padding:.78rem .9rem; margin:.45rem 0; box-shadow:0 7px 18px rgba(15,23,42,.04); }
.alert-card.red { border-left-color:#ef4444; }
.alert-card.green { border-left-color:#22c55e; }
.alert-card.blue { border-left-color:#3b82f6; }
.alert-title { color:#0f172a; font-weight:750; }
.alert-copy { color:#64748b; font-size:.84rem; margin-top:.15rem; }
.status-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.55rem; margin:.35rem 0 1rem; }
.status-tile { background:#fff; border:1px solid #e2e8f0; border-radius:13px; padding:.72rem .8rem; }
.status-name { color:#64748b; font-size:.8rem; }
.status-value { color:#0f172a; font-size:1.25rem; font-weight:850; margin-top:.15rem; }
.status-dot { display:inline-block; width:.55rem; height:.55rem; border-radius:999px; margin-right:.35rem; }
.dot-green{background:#22c55e}.dot-blue{background:#3b82f6}.dot-orange{background:#f59e0b}.dot-red{background:#ef4444}.dot-purple{background:#8b5cf6}
.dashboard-section { margin-top:.7rem; }
@media (max-width: 900px) { .status-grid { grid-template-columns:1fr; } }
@media (max-width: 900px) { .block-container { padding-left: .8rem; padding-right: .8rem; } .main h1 { font-size: 1.8rem !important; } .erp-hero { align-items:flex-start; flex-direction:column; } }

/* Module 01 — Enterprise Dashboard */
.login-shell{max-width:760px;margin:4vh auto 1.25rem;padding:2.2rem;border-radius:24px;text-align:center;background:linear-gradient(135deg,#0b1736,#1d4ed8 62%,#0891b2);box-shadow:0 24px 64px rgba(15,23,42,.22)}
.login-title{color:#fff;font-size:2.35rem;font-weight:900;letter-spacing:-.04em}.login-subtitle{color:#dbeafe;margin-top:.5rem;font-weight:600}
.exec-strip{display:flex;justify-content:space-between;gap:1rem;align-items:center;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:.9rem 1rem;margin-bottom:1rem;box-shadow:0 10px 24px rgba(15,23,42,.05)}
.exec-strip-title{font-weight:850;color:#0f172a}.exec-strip-copy{font-size:.84rem;color:#64748b;margin-top:.12rem}.exec-chip{border-radius:999px;padding:.34rem .65rem;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;font-size:.76rem;font-weight:800;white-space:nowrap}
.insight-card{background:linear-gradient(145deg,#0f172a,#1e3a8a);border-radius:16px;padding:1rem 1.05rem;color:#fff;margin:.45rem 0;box-shadow:0 12px 28px rgba(15,23,42,.16)}.insight-card strong{font-size:.92rem}.insight-card div{color:#dbeafe;font-size:.84rem;margin-top:.2rem}
.exec-section-label{font-size:.76rem;font-weight:900;letter-spacing:.10em;text-transform:uppercase;color:#64748b;margin:.8rem 0 .45rem}


/* Module 08 — AI Executive Command Center */
.ai-command-banner{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1.1rem 1.2rem;margin-bottom:1rem;border-radius:18px;background:linear-gradient(115deg,#071426,#172554 58%,#0e7490);box-shadow:0 18px 44px rgba(15,23,42,.18);color:#fff}.ai-command-title{font-size:1.25rem;font-weight:900;letter-spacing:-.02em}.ai-command-sub{font-size:.84rem;color:#dbeafe;margin-top:.25rem}.ai-live-chip{padding:.36rem .7rem;border-radius:999px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);font-size:.76rem;font-weight:850;white-space:nowrap}.ai-insight{border:1px solid #dbeafe;border-left:5px solid #2563eb;border-radius:14px;background:#fff;padding:.85rem 1rem;margin:.5rem 0;box-shadow:0 8px 20px rgba(15,23,42,.05)}.ai-insight.warn{border-left-color:#d97706}.ai-insight.risk{border-left-color:#dc2626}.ai-insight.good{border-left-color:#16a34a}.ai-insight-title{font-size:.82rem;font-weight:900;color:#0f172a}.ai-insight-copy{font-size:.82rem;color:#475569;margin-top:.18rem}.command-question{padding:.8rem 1rem;border-radius:14px;background:linear-gradient(90deg,#eff6ff,#ecfeff);border:1px solid #bfdbfe;color:#1e3a8a;font-weight:750;margin-bottom:.8rem}.forecast-note{font-size:.78rem;color:#64748b;margin-top:.35rem}

/* ---------------- Enterprise grouped sidebar navigation ---------------- */
[data-testid="stSidebar"] .nav-group-label {
    color: #7fa8e0;
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin: 1rem 0 .3rem;
    padding: 0 .15rem;
}
[data-testid="stSidebar"] .stButton { margin: .05rem 0; }
[data-testid="stSidebar"] .stButton > button {
    display: flex !important;
    align-items: center;
    gap: .5rem;
    width: 100%;
    text-align: left;
    justify-content: flex-start !important;
    background: transparent !important;
    color: #cbd8ee !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    padding: .5rem .65rem !important;
    min-height: 2.35rem;
    transition: all .15s ease;
}
[data-testid="stSidebar"] .stButton > button p { text-align: left !important; font-weight: 600; }
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.09) !important;
    color: #fff !important;
    transform: translateX(2px);
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, rgba(59,130,246,.55), rgba(6,182,212,.30)) !important;
    color: #fff !important;
    border-color: rgba(147,197,253,.4) !important;
    box-shadow: 0 7px 18px rgba(2,8,23,.25) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] p { color: #fff !important; font-weight: 750; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12); margin: .6rem 0; }

/* Breadcrumb + status badges to echo a commercial PMS look */
.erp-breadcrumb { font-size: .78rem; color: #dbeafe; opacity: .85; margin-bottom: .2rem; }
.status-pill { display: inline-block; padding: .2rem .6rem; border-radius: 999px; font-size: .76rem; font-weight: 750; }
</style>
""", unsafe_allow_html=True)

ALL_MODULES = [
    "Dashboard","Reservations","Front Desk","Rooms","Restaurant POS",
    "Kitchen Display","Kitchen Performance","Housekeeping","Inventory",
    "Purchasing","Maintenance","Payments","Expenses","Finance Control Tower",
    "AI Command Center","Reports","User Access"
]

MODULE_ICONS = {
    "Dashboard": "📊", "Reservations": "🗓️", "Front Desk": "🛎️",
    "Rooms": "🛏️", "Restaurant POS": "🍽️", "Kitchen Display": "👨‍🍳",
    "Kitchen Performance": "⏱️", "Housekeeping": "🧹", "Inventory": "📦",
    "Purchasing": "🛒", "Maintenance": "🛠️", "Payments": "💳",
    "Expenses": "🧾", "Finance Control Tower": "💹", "AI Command Center": "🤖",
    "Reports": "📑", "User Access": "👥"
}

# ---------------- Password hashing ----------------
def hash_password(plain, salt=None):
    if salt is None:
        salt_bytes = os.urandom(16)
    else:
        salt_bytes = bytes.fromhex(salt) if isinstance(salt, str) else salt
    dk = hashlib.pbkdf2_hmac('sha256', plain.encode('utf-8'), salt_bytes, 100000)
    return f"pbkdf2${salt_bytes.hex()}${dk.hex()}"

def verify_password(plain, stored):
    if not stored:
        return False
    stored = str(stored)
    if stored.startswith("pbkdf2$"):
        parts = stored.split("$")
        if len(parts) != 3:
            return False
        _, salt_hex, hash_hex = parts
        salt_bytes = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac('sha256', plain.encode('utf-8'), salt_bytes, 100000)
        return hmac.compare_digest(dk.hex(), hash_hex)
    # legacy plaintext fallback — allows old demo rows to still log in once
    return hmac.compare_digest(plain, stored)

# ---------------- Database ----------------
def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def execute(sql, params=()):
    with conn() as c:
        c.execute(sql, params)
        c.commit()

def query(sql, params=()):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)

def date_range_filter(df, date_col, start_date, end_date):
    """Return rows whose date column falls within the inclusive date range."""
    if df is None or df.empty or date_col not in df.columns:
        return df

    result = df.copy()
    dt = pd.to_datetime(result[date_col], errors="coerce")
    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()
    mask = dt.notna() & (dt.dt.date >= start) & (dt.dt.date <= end)
    return result.loc[mask].copy()

def scalar(sql, params=(), default=0):
    with conn() as c:
        row = c.execute(sql, params).fetchone()
    return default if not row or row[0] is None else row[0]

def next_code(prefix, table, id_column=None):
    # id_column is accepted for call-site clarity (e.g. next_code("HKT", "housekeeping_tasks", "task_id"))
    # but the sequence itself is always derived from the table's row count.
    n = int(scalar(f"SELECT COUNT(*) FROM {table}", default=0)) + 1
    return f"{prefix}{n:05d}"

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rooms(
            room_no TEXT PRIMARY KEY,
            room_type TEXT,
            rate REAL,
            status TEXT,
            housekeeping TEXT
        );

        CREATE TABLE IF NOT EXISTS reservations(
            reservation_id TEXT PRIMARY KEY,
            guest_name TEXT,
            mobile TEXT,
            id_number TEXT,
            room_no TEXT,
            checkin_date TEXT,
            checkout_date TEXT,
            adults INTEGER,
            children INTEGER,
            status TEXT,
            room_rate REAL,
            deposit REAL,
            source TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS menu(
            item_code TEXT PRIMARY KEY,
            item_name TEXT,
            category TEXT,
            price REAL,
            station TEXT,
            target_minutes INTEGER,
            ingredient TEXT,
            qty_per_item REAL,
            unit TEXT
        );

        CREATE TABLE IF NOT EXISTS orders(
            order_id TEXT PRIMARY KEY,
            kot_no TEXT,
            order_time TEXT,
            order_type TEXT,
            table_room TEXT,
            guest_ref TEXT,
            item_code TEXT,
            item_name TEXT,
            qty REAL,
            rate REAL,
            amount REAL,
            station TEXT,
            chef TEXT,
            priority TEXT,
            instructions TEXT,
            target_minutes INTEGER,
            started_at TEXT,
            ready_at TEXT,
            served_at TEXT,
            status TEXT,
            payment_status TEXT
        );

        CREATE TABLE IF NOT EXISTS inventory(
            item_code TEXT PRIMARY KEY,
            item_name TEXT,
            category TEXT,
            unit TEXT,
            opening_qty REAL,
            received_qty REAL,
            issued_qty REAL,
            reorder_level REAL,
            unit_cost REAL
        );

        CREATE TABLE IF NOT EXISTS suppliers(
            supplier_id TEXT PRIMARY KEY,
            supplier_name TEXT,
            vat_no TEXT,
            mobile TEXT,
            email TEXT,
            payment_terms INTEGER
        );

        CREATE TABLE IF NOT EXISTS purchase_orders(
            po_no TEXT PRIMARY KEY,
            po_date TEXT,
            supplier_id TEXT,
            supplier_name TEXT,
            item_code TEXT,
            item_name TEXT,
            qty REAL,
            unit_cost REAL,
            vat_rate REAL,
            total REAL,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS payments(
            payment_id TEXT PRIMARY KEY,
            payment_date TEXT,
            reference TEXT,
            customer TEXT,
            payment_method TEXT,
            amount REAL,
            payment_type TEXT
        );

        CREATE TABLE IF NOT EXISTS expenses(
            expense_id TEXT PRIMARY KEY,
            expense_date TEXT,
            category TEXT,
            description TEXT,
            amount REAL
        );

        CREATE TABLE IF NOT EXISTS maintenance(
            ticket_id TEXT PRIMARY KEY,
            room_no TEXT,
            issue TEXT,
            priority TEXT,
            assigned_to TEXT,
            status TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS goods_receipts(
            grn_no TEXT PRIMARY KEY,
            grn_date TEXT,
            po_no TEXT,
            supplier_name TEXT,
            item_code TEXT,
            item_name TEXT,
            ordered_qty REAL,
            received_qty REAL,
            rejected_qty REAL,
            accepted_qty REAL,
            warehouse TEXT,
            received_by TEXT,
            remarks TEXT,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS supplier_invoices(
            invoice_id TEXT PRIMARY KEY,
            invoice_no TEXT,
            invoice_date TEXT,
            po_no TEXT,
            grn_no TEXT,
            supplier_name TEXT,
            subtotal REAL,
            vat_amount REAL,
            total_amount REAL,
            due_date TEXT,
            booked_by TEXT,
            booked_at TEXT,
            status TEXT
        );
        """)
        c.commit()

    if scalar("SELECT COUNT(*) FROM users") == 0:
        seed_users = [
            ("admin", "admin123", "Admin", "System Administrator"),
            ("manager", "manager123", "Manager", "Hotel Manager"),
            ("reception", "front123", "Reception", "Front Desk"),
            ("restaurant", "pos123", "Restaurant", "Restaurant Cashier"),
            ("kitchen", "kitchen123", "Kitchen", "Kitchen Team"),
            ("housekeeping", "house123", "Housekeeping", "Housekeeping Team"),
            ("accounts", "accounts123", "Accounts", "Accounts Team")
        ]
        users = [(u, hash_password(p), r, n) for (u, p, r, n) in seed_users]
        with conn() as c:
            c.executemany("INSERT INTO users VALUES(?,?,?,?)", users)
            c.commit()

    if scalar("SELECT COUNT(*) FROM rooms") == 0:
        rows = []
        for i in range(1, 31):
            typ = "Standard" if i <= 15 else "Deluxe" if i <= 25 else "Suite"
            rate = 250 if typ == "Standard" else 400 if typ == "Deluxe" else 650
            rows.append((str(100+i), typ, rate, "Available", "Clean"))
        with conn() as c:
            c.executemany("INSERT INTO rooms VALUES(?,?,?,?,?)", rows)
            c.commit()

    if scalar("SELECT COUNT(*) FROM inventory") == 0:
        inv = [
            ("INV001","Rice","Food","kg",50,0,0,15,7.5),
            ("INV002","Chicken","Food","kg",35,0,0,10,18),
            ("INV003","Cooking Oil","Food","litre",30,0,0,8,9),
            ("INV004","Coffee Beans","Beverage","kg",12,0,0,4,42),
            ("INV005","Soft Drinks","Beverage","bottle",120,0,0,30,2.5),
            ("INV006","Housekeeping Kit","Housekeeping","set",80,0,0,20,6)
        ]
        with conn() as c:
            c.executemany("INSERT INTO inventory VALUES(?,?,?,?,?,?,?,?,?)", inv)
            c.commit()

    if scalar("SELECT COUNT(*) FROM menu") == 0:
        menu = [
            ("M001","Chicken Biryani","Main Course",38,"Indian",20,"Chicken",0.20,"kg"),
            ("M002","Veg Biryani","Main Course",30,"Indian",18,"Rice",0.25,"kg"),
            ("M003","Grilled Chicken","Main Course",52,"Grill",25,"Chicken",0.25,"kg"),
            ("M004","French Fries","Snacks",15,"Fry",10,"Cooking Oil",0.03,"litre"),
            ("M005","Coffee","Beverage",10,"Beverage Bar",5,"Coffee Beans",0.02,"kg"),
            ("M006","Soft Drink","Beverage",8,"Beverage Bar",2,"Soft Drinks",1,"bottle"),
            ("M007","Breakfast Buffet","Breakfast",45,"Main Kitchen",15,"Rice",0.10,"kg"),
            ("M008","Ice Cream","Dessert",16,"Dessert",3,"",0,"")
        ]
        with conn() as c:
            c.executemany("INSERT INTO menu VALUES(?,?,?,?,?,?,?,?,?)", menu)
            c.commit()


init_db()

def migrate_purchase_orders():
    existing = query("PRAGMA table_info(purchase_orders)")
    cols = set(existing["name"].tolist()) if not existing.empty else set()

    additions = {
        "payment_method": "TEXT DEFAULT 'Bank Transfer'",
        "payment_terms_days": "INTEGER DEFAULT 30",
        "requested_by": "TEXT DEFAULT ''",
        "requested_username": "TEXT DEFAULT ''",
        "approval_level": "TEXT DEFAULT 'Manager'",
        "approved_by": "TEXT DEFAULT ''",
        "approved_at": "TEXT DEFAULT ''",
        "rejection_reason": "TEXT DEFAULT ''",
        "payment_status": "TEXT DEFAULT 'Unpaid'",
        "paid_amount": "REAL DEFAULT 0",
        "received_at": "TEXT DEFAULT ''",
        "grn_no": "TEXT DEFAULT ''",
        "invoice_status": "TEXT DEFAULT 'Not Booked'",
        "cancelled_by": "TEXT DEFAULT ''",
        "cancelled_at": "TEXT DEFAULT ''",
        "cancellation_reason": "TEXT DEFAULT ''"
    }

    for column, definition in additions.items():
        if column not in cols:
            execute(f"ALTER TABLE purchase_orders ADD COLUMN {column} {definition}")

migrate_purchase_orders()

def migrate_supplier_invoices():
    existing = query("PRAGMA table_info(supplier_invoices)")
    cols = set(existing["name"].tolist()) if not existing.empty else set()
    additions = {
        "paid_amount": "REAL DEFAULT 0",
        "payment_status": "TEXT DEFAULT 'Unpaid'",
        "payment_reference": "TEXT DEFAULT ''",
        "paid_at": "TEXT DEFAULT ''"
    }
    for column, definition in additions.items():
        if column not in cols:
            execute(f"ALTER TABLE supplier_invoices ADD COLUMN {column} {definition}")

migrate_supplier_invoices()


def migrate_housekeeping_enterprise():
    """Create enterprise housekeeping workflow tables without changing existing room data."""
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS housekeeping_tasks(
            task_id TEXT PRIMARY KEY,
            task_date TEXT,
            room_no TEXT,
            task_type TEXT,
            priority TEXT,
            assigned_to TEXT,
            status TEXT,
            start_time TEXT,
            completed_time TEXT,
            inspected_by TEXT,
            inspection_status TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS housekeeping_checklists(
            checklist_id TEXT PRIMARY KEY,
            task_id TEXT,
            room_no TEXT,
            linen_changed INTEGER DEFAULT 0,
            bathroom_cleaned INTEGER DEFAULT 0,
            amenities_replenished INTEGER DEFAULT 0,
            minibar_checked INTEGER DEFAULT 0,
            floor_cleaned INTEGER DEFAULT 0,
            maintenance_issue INTEGER DEFAULT 0,
            lost_found_item INTEGER DEFAULT 0,
            remarks TEXT,
            completed_by TEXT,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS lost_and_found(
            record_id TEXT PRIMARY KEY,
            found_date TEXT,
            room_no TEXT,
            item_description TEXT,
            found_by TEXT,
            storage_location TEXT,
            guest_name TEXT,
            status TEXT,
            released_to TEXT,
            released_at TEXT,
            notes TEXT
        );
        """)
        c.commit()

migrate_housekeeping_enterprise()

def migrate_users():
    existing = query("PRAGMA table_info(users)")
    cols = set(existing["name"].tolist()) if not existing.empty else set()
    additions = {
        "email": "TEXT DEFAULT ''",
        "mobile": "TEXT DEFAULT ''",
        "department": "TEXT DEFAULT ''",
        "is_active": "INTEGER DEFAULT 1",
        "created_at": "TEXT DEFAULT ''",
        "last_login": "TEXT DEFAULT ''"
    }
    for column, definition in additions.items():
        if column not in cols:
            execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")


def migrate_inventory_approval():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS stock_adjustment_batches(
            batch_no TEXT PRIMARY KEY,
            batch_date TEXT,
            adjustment_source TEXT,
            file_name TEXT,
            location TEXT,
            total_lines INTEGER,
            total_increase_qty REAL,
            total_decrease_qty REAL,
            total_variance_value REAL,
            submitted_by TEXT,
            submitted_username TEXT,
            submitted_at TEXT,
            status TEXT,
            reviewed_by TEXT,
            reviewed_username TEXT,
            reviewed_at TEXT,
            review_comments TEXT,
            posted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS stock_adjustment_lines(
            line_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_no TEXT,
            item_code TEXT,
            item_name TEXT,
            adjustment_type TEXT,
            quantity REAL,
            reason TEXT,
            system_qty REAL,
            projected_qty REAL,
            difference_qty REAL,
            unit_cost REAL,
            variance_value REAL,
            validation_status TEXT,
            validation_message TEXT,
            FOREIGN KEY(batch_no) REFERENCES stock_adjustment_batches(batch_no)
        );

        CREATE TABLE IF NOT EXISTS inventory_audit_log(
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_no TEXT,
            item_code TEXT,
            item_name TEXT,
            transaction_type TEXT,
            before_qty REAL,
            change_qty REAL,
            after_qty REAL,
            unit_cost REAL,
            value_impact REAL,
            reason TEXT,
            action_by TEXT,
            action_username TEXT,
            action_at TEXT,
            approval_by TEXT,
            approval_at TEXT
        );

        CREATE TABLE IF NOT EXISTS opening_stock_requests(
            item_code TEXT PRIMARY KEY,
            item_name TEXT,
            requested_qty REAL,
            requested_by TEXT,
            requested_username TEXT,
            requested_at TEXT,
            status TEXT
        );
        """)
        c.commit()

def migrate_user_access():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS user_module_access(
            username TEXT,
            module TEXT,
            PRIMARY KEY(username, module)
        );

        CREATE TABLE IF NOT EXISTS user_access_mode(
            username TEXT PRIMARY KEY,
            use_custom INTEGER DEFAULT 0
        );
        """)
        c.commit()

def migrate_finance_control():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS finance_settings(
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_by TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS chart_of_accounts(
            account_code TEXT PRIMARY KEY,
            account_name TEXT,
            account_type TEXT,
            parent_code TEXT,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS journal_headers(
            journal_no TEXT PRIMARY KEY,
            journal_date TEXT,
            reference TEXT,
            description TEXT,
            status TEXT,
            created_by TEXT,
            created_at TEXT,
            approved_by TEXT,
            approved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS journal_lines(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_no TEXT,
            account_code TEXT,
            department TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            narration TEXT
        );

        CREATE TABLE IF NOT EXISTS budgets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_year INTEGER,
            month_no INTEGER,
            department TEXT,
            account_code TEXT,
            budget_amount REAL,
            UNIQUE(fiscal_year, month_no, department, account_code)
        );

        CREATE TABLE IF NOT EXISTS bank_accounts(
            bank_code TEXT PRIMARY KEY,
            bank_name TEXT,
            account_name TEXT,
            iban TEXT,
            opening_balance REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS bank_transactions(
            transaction_id TEXT PRIMARY KEY,
            bank_code TEXT,
            transaction_date TEXT,
            transaction_type TEXT,
            reference TEXT,
            description TEXT,
            amount REAL,
            reconciled INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TEXT
        );
        """)
        if c.execute("SELECT COUNT(*) FROM chart_of_accounts").fetchone()[0] == 0:
            coa = [
                ("1000","Cash and Cash Equivalents","Asset",None,1),
                ("1010","Cash on Hand","Asset","1000",1),
                ("1020","Bank Accounts","Asset","1000",1),
                ("1100","Accounts Receivable","Asset",None,1),
                ("1200","Inventory","Asset",None,1),
                ("2000","Accounts Payable","Liability",None,1),
                ("2100","VAT Payable","Liability",None,1),
                ("3000","Owner Equity","Equity",None,1),
                ("4000","Room Revenue","Revenue",None,1),
                ("4100","Restaurant Revenue","Revenue",None,1),
                ("4200","Other Revenue","Revenue",None,1),
                ("5000","Cost of Sales","Expense",None,1),
                ("5100","Food Cost","Expense","5000",1),
                ("6000","Operating Expenses","Expense",None,1),
                ("6100","Payroll Expense","Expense","6000",1),
                ("6200","Utilities Expense","Expense","6000",1),
                ("6300","Maintenance Expense","Expense","6000",1),
                ("6400","Housekeeping Expense","Expense","6000",1),
            ]
            c.executemany("INSERT INTO chart_of_accounts VALUES(?,?,?,?,?)", coa)
        if c.execute("SELECT COUNT(*) FROM finance_settings WHERE setting_key='business_date'").fetchone()[0] == 0:
            c.execute("INSERT INTO finance_settings VALUES(?,?,?,?)", ('business_date', str(date.today()), 'system', datetime.now().isoformat(timespec='seconds')))
        if c.execute("SELECT COUNT(*) FROM finance_settings WHERE setting_key='period_lock'").fetchone()[0] == 0:
            c.execute("INSERT INTO finance_settings VALUES(?,?,?,?)", ('period_lock', '', 'system', datetime.now().isoformat(timespec='seconds')))
        if c.execute("SELECT COUNT(*) FROM bank_accounts").fetchone()[0] == 0:
            c.execute("INSERT INTO bank_accounts VALUES(?,?,?,?,?,?)", ('BANK-001','Primary Bank','Hotel Operating Account','SA0000000000000000000000',0,1))
        c.commit()

migrate_users()
migrate_inventory_approval()
migrate_user_access()
migrate_finance_control()
approvals.init_approval_schema(conn)

# ---------------- Helpers ----------------
def money(v):
    return f"SAR {float(v or 0):,.2f}"

def _status_badge_style(val):
    """Pandas Styler cell formatter: colored pill background for status columns
    (Reserved / Checked-in / Checked-out / No Show / Cancelled), similar to the
    status chips used in commercial PMS reservation grids."""
    v = str(val).strip().lower()
    colors = {
        "reserved": ("#dbeafe", "#1d4ed8"),
        "checked-in": ("#dcfce7", "#15803d"),
        "checked-out": ("#e2e8f0", "#475569"),
        "no show": ("#fee2e2", "#b91c1c"),
        "cancelled": ("#fee2e2", "#b91c1c"),
    }
    bg, fg = colors.get(v, ("#eef2ff", "#4338ca"))
    return f"background-color:{bg};color:{fg};font-weight:700;border-radius:6px;"

def style_status_column(df, column="status"):
    """Returns a pandas Styler with a colored badge on the given status column,
    falling back to the plain DataFrame if the column is missing/empty or the
    installed pandas version doesn't support Styler.map/applymap."""
    if df is None or df.empty or column not in df.columns:
        return df
    try:
        styler = df.style
        fn = styler.map if hasattr(styler, "map") else styler.applymap
        return fn(_status_badge_style, subset=[column])
    except Exception:
        return df

def excel_file(sheets):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return out.getvalue()

def stock_df():
    df = query("""
        SELECT item_code, item_name, category, unit, opening_qty, received_qty,
               issued_qty, reorder_level, unit_cost,
               opening_qty + received_qty - issued_qty AS available_qty,
               (opening_qty + received_qty - issued_qty) * unit_cost AS stock_value
        FROM inventory
    """)
    df["stock_status"] = df.apply(
        lambda r: "REORDER" if r["available_qty"] <= r["reorder_level"] else "OK", axis=1
    )
    return df

def next_adjustment_batch():
    today = date.today().strftime("%Y%m%d")
    prefix = f"ADJ-{today}-"
    n = int(scalar(
        "SELECT COUNT(*) FROM stock_adjustment_batches WHERE batch_no LIKE ?",
        (prefix + "%",),
        default=0
    )) + 1
    return f"{prefix}{n:04d}"


def normalize_adjustment_type(value):
    text = str(value or "").strip().lower()
    received = {"stock received", "received", "receipt", "increase", "add", "stock in"}
    issued = {"stock issued", "stock issued / used", "issued", "used", "decrease", "deduct", "stock out"}
    if text in received:
        return "Stock Received"
    if text in issued:
        return "Stock Issued / Used"
    return ""


def adjustment_preview(upload_df):
    required = ["Item", "Adjustment Type", "Quantity", "Remarks"]
    result = upload_df.copy()
    result.columns = [str(c).strip() for c in result.columns]
    for col in required:
        if col not in result.columns:
            result[col] = ""
    result = result[required].copy()
    result = result.dropna(how="all").reset_index(drop=True)

    inventory = query("""
        SELECT item_code,item_name,unit,unit_cost,
               opening_qty+received_qty-issued_qty AS system_qty
        FROM inventory
    """)
    by_name = {str(r.item_name).strip().lower(): r for r in inventory.itertuples()}
    by_code = {str(r.item_code).strip().lower(): r for r in inventory.itertuples()}

    rows = []
    seen = set()
    for idx, row in result.iterrows():
        item = str(row["Item"] or "").strip()
        adj_type = normalize_adjustment_type(row["Adjustment Type"])
        try:
            qty = float(row["Quantity"])
        except Exception:
            qty = 0.0
        reason = str(row["Remarks"] or "").strip()
        inv = by_code.get(item.lower()) or by_name.get(item.lower())
        status = "Valid"
        message = "Ready for submission"
        item_code = ""
        item_name = item
        system_qty = 0.0
        projected_qty = 0.0
        unit_cost = 0.0

        if not item:
            status, message = "Error", "Item is required"
        elif inv is None:
            status, message = "Error", "Item not found in inventory"
        else:
            item_code = str(inv.item_code)
            item_name = str(inv.item_name)
            system_qty = float(inv.system_qty or 0)
            unit_cost = float(inv.unit_cost or 0)
            key = item_code.lower()
            if key in seen:
                status, message = "Error", "Duplicate item in upload"
            seen.add(key)

        if not adj_type:
            status, message = "Error", "Adjustment Type must be Stock Received or Stock Issued / Used"
        if qty <= 0:
            status, message = "Error", "Quantity must be greater than zero"
        if not reason:
            status, message = "Error", "Remarks / reason is required"

        signed_qty = qty if adj_type == "Stock Received" else -qty
        projected_qty = system_qty + signed_qty
        if inv is not None and projected_qty < -0.000001:
            status, message = "Error", f"Insufficient stock; available {system_qty:.2f}"

        rows.append({
            "Row": idx + 2,
            "Item Code": item_code,
            "Item": item_name,
            "Adjustment Type": adj_type or str(row["Adjustment Type"]),
            "Quantity": qty,
            "System Quantity": system_qty,
            "Projected Quantity": projected_qty,
            "Difference": signed_qty,
            "Unit Cost": unit_cost,
            "Variance Value": signed_qty * unit_cost,
            "Remarks": reason,
            "Validation": status,
            "Message": message
        })
    return pd.DataFrame(rows)


def role_default_modules(role):
    access = {
        "Admin": None,
        "Manager": None,
        "Reception": {"Dashboard","Reservations","Front Desk","Rooms","Maintenance"},
        "Restaurant": {"Dashboard","Restaurant POS","Payments"},
        "Kitchen": {"Dashboard","Kitchen Display","Kitchen Performance","Inventory"},
        "Housekeeping": {"Dashboard","Housekeeping","Maintenance"},
        "Accounts": {"Dashboard","Payments","Expenses","Purchasing","Inventory","Finance Control Tower","Reports"}
    }
    allowed = access.get(role)
    return set(ALL_MODULES) if allowed is None else allowed


def get_access_mode(username):
    return int(scalar("SELECT use_custom FROM user_access_mode WHERE username=?", (username,), default=0))


def get_user_custom_modules(username):
    """Returns a set of allowed modules (possibly EMPTY on purpose) if this
    user has custom access turned on, or None if they're on role defaults."""
    if not get_access_mode(username):
        return None
    df = query("SELECT module FROM user_module_access WHERE username=?", (username,))
    return set(df["module"].tolist())


def page_allowed(username, page, role):
    custom = get_user_custom_modules(username)
    allowed = custom if custom is not None else role_default_modules(role)
    if role == "Admin":
        # Admins can never be locked out of the modules needed to fix access.
        allowed = set(allowed) | {"Dashboard", "User Access"}
    return page in allowed


def sync_po_payment_rollup(po_no):
    """Recomputes purchase_orders.paid_amount / payment_status as an aggregate
    of that PO's supplier_invoices rows. Invoice-level rows are the source of
    truth for payment tracking; this rollup exists only so older parts of the
    UI (Cancel PO, Approval Queue table) that display a single PO-level status
    keep working sensibly when a PO has multiple invoices."""
    invoices = query(
        "SELECT total_amount, paid_amount, payment_status FROM supplier_invoices WHERE po_no=?",
        (po_no,)
    )
    if invoices.empty:
        return
    total_paid = float(invoices["paid_amount"].fillna(0).astype(float).sum())
    all_paid = bool((invoices["payment_status"] == "Paid").all())
    any_paid = total_paid > 0
    status = "Paid" if all_paid else ("Partially Paid" if any_paid else "Unpaid")
    execute(
        "UPDATE purchase_orders SET paid_amount=?, payment_status=? WHERE po_no=?",
        (total_paid, status, po_no)
    )

# ---------------- Login ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("""
    <div class="login-shell">
      <div class="login-title">🏨 Hotel Control Tower</div>
      <div class="login-subtitle">Enterprise Operations • Finance • Guest Experience</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Hotel, restaurant, kitchen, inventory, purchasing, maintenance and finance in one system.")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login = st.form_submit_button("Login", type="primary")
    if login:
        user_row = query(
            """SELECT username, role, full_name, password
               FROM users
               WHERE username=? AND COALESCE(is_active,1)=1""",
            (username,)
        )
        if user_row.empty or not verify_password(password, user_row.iloc[0]["password"]):
            st.error("Invalid username or password.")
        else:
            stored_password = str(user_row.iloc[0]["password"])
            if not stored_password.startswith("pbkdf2$"):
                # Transparent upgrade: first successful login on a legacy
                # plaintext row re-saves it hashed.
                execute("UPDATE users SET password=? WHERE username=?", (hash_password(password), username))
            st.session_state.user = user_row.iloc[0][["username", "role", "full_name"]].to_dict()
            execute(
                "UPDATE users SET last_login=? WHERE username=?",
                (datetime.now().isoformat(timespec="seconds"), username)
            )
            st.rerun()

    st.info("Demo admin login: admin / admin123")
    st.stop()

user = st.session_state.user
st.sidebar.markdown("""
<div class="erp-brand-card">
  <div class="erp-brand-name">🏨 Hotel Control Tower</div>
  <div class="erp-brand-sub">Operations • Finance • Guest Experience</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown(
    f"""<div class="erp-user-chip"><strong>👤 {user['full_name']}</strong><br>
    <span style="color:#bfdbfe;font-size:.82rem">{user['role']} access</span></div>""",
    unsafe_allow_html=True
)

visible_pages = [p for p in ALL_MODULES if page_allowed(user["username"], p, user["role"])]

if not visible_pages:
    st.warning("You currently have no module access. Contact the system administrator.")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    st.stop()

# Grouped navigation (Front Office / Housekeeping / POS & F&B / Inventory /
# Finance / Insights sections) instead of one long flat list, to match a
# commercial hotel PMS sidebar layout.
NAV_GROUPS = [
    ("MAIN", ["Dashboard"]),
    ("FRONT OFFICE", ["Reservations", "Front Desk", "Rooms"]),
    ("POS & F&B", ["Restaurant POS", "Kitchen Display", "Kitchen Performance"]),
    ("HOUSEKEEPING", ["Housekeeping", "Maintenance"]),
    ("INVENTORY & PURCHASING", ["Inventory", "Purchasing"]),
    ("FINANCE", ["Payments", "Expenses", "Finance Control Tower"]),
    ("INSIGHTS", ["AI Command Center", "Reports"]),
    ("ADMIN", ["User Access"]),
]
page_to_group = {p: g for g, ps in NAV_GROUPS for p in ps}

if st.session_state.get("nav_page") not in visible_pages:
    st.session_state["nav_page"] = visible_pages[0]
page = st.session_state["nav_page"]

for group_label, group_pages in NAV_GROUPS:
    items = [p for p in group_pages if p in visible_pages]
    if not items:
        continue
    st.sidebar.markdown(f"<div class='nav-group-label'>{group_label}</div>", unsafe_allow_html=True)
    for p in items:
        if st.sidebar.button(
            f"{MODULE_ICONS.get(p, '•')}  {p}",
            key=f"navbtn_{p}",
            use_container_width=True,
            type="primary" if p == page else "secondary",
        ):
            st.session_state["nav_page"] = p
            st.rerun()

st.sidebar.markdown("<hr/>", unsafe_allow_html=True)
if st.sidebar.button("🚪  Logout", use_container_width=True):
    st.session_state.user = None
    st.rerun()

page_group = page_to_group.get(page, "MAIN")
st.markdown(
    f"""<div class="erp-hero">
      <div><div class="erp-breadcrumb">Home / {page_group} / {page}</div>
      <div class="erp-hero-title">{MODULE_ICONS.get(page, '🏨')} {page}</div>
      <div class="erp-hero-copy">Hotel operations control center • {datetime.now().strftime('%A, %d %B %Y')}</div></div>
      <div class="erp-live">● Live workspace</div>
    </div>""",
    unsafe_allow_html=True
)

# ---------------- User Access ----------------
if page == "User Access":
    st.title("User Access Management")

    if user["role"] != "Admin":
        st.error("Only the System Administrator can manage users.")
        st.stop()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "User Register",
        "Create User",
        "Reset Password",
        "Activate / Deactivate",
        "Manage Access"
    ])

    with tab1:
        users_df = query("""
            SELECT username, full_name, role, department, email, mobile,
                   CASE WHEN COALESCE(is_active,1)=1 THEN 'Active' ELSE 'Inactive' END AS status,
                   created_at, last_login
            FROM users
            ORDER BY username
        """)
        st.dataframe(users_df, use_container_width=True, hide_index=True)

        role_access = pd.DataFrame([
            ["Admin", "All modules and user management"],
            ["Manager", "All operational and management modules"],
            ["Reception", "Dashboard, Reservations, Front Desk, Rooms, Maintenance"],
            ["Restaurant", "Dashboard, Restaurant POS, Payments"],
            ["Kitchen", "Dashboard, Kitchen Display, Kitchen Performance, Inventory"],
            ["Housekeeping", "Dashboard, Housekeeping, Maintenance"],
            ["Accounts", "Dashboard, Payments, Expenses, Purchasing, Inventory, Finance Control Tower, Reports"]
        ], columns=["Role", "Access"])
        st.caption("Default access by role. Individual users can be given custom access under Manage Access.")
        st.dataframe(role_access, use_container_width=True, hide_index=True)

    with tab2:
        with st.form("create_user", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            new_username = c1.text_input("Username")
            full_name = c2.text_input("Full Name")
            role = c3.selectbox(
                "Role",
                ["Admin","Manager","Reception","Restaurant","Kitchen","Housekeeping","Accounts"]
            )

            c1, c2, c3 = st.columns(3)
            department = c1.text_input("Department")
            email = c2.text_input("Email")
            mobile = c3.text_input("Mobile")

            c1, c2 = st.columns(2)
            password = c1.text_input("Temporary Password", type="password")
            confirm_password = c2.text_input("Confirm Password", type="password")
            create_user = st.form_submit_button("Create User", type="primary")

        if create_user:
            if not new_username.strip() or not full_name.strip():
                st.error("Username and full name are required.")
            elif len(password) < 6:
                st.error("Password must contain at least 6 characters.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            elif scalar("SELECT COUNT(*) FROM users WHERE LOWER(username)=LOWER(?)",(new_username.strip(),)) > 0:
                st.error("Username already exists.")
            else:
                execute(
                    """INSERT INTO users(
                        username,password,role,full_name,email,mobile,department,
                        is_active,created_at,last_login
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        new_username.strip(), hash_password(password), role, full_name.strip(),
                        email.strip(), mobile.strip(), department.strip(), 1,
                        datetime.now().isoformat(timespec="seconds"), ""
                    )
                )
                st.success(f"User {new_username.strip()} created successfully.")
                st.rerun()

    with tab3:
        users_df = query("SELECT username, full_name FROM users ORDER BY username")
        username_to_reset = st.selectbox("Select User", users_df["username"].tolist(), key="reset_user")
        c1, c2 = st.columns(2)
        new_password = c1.text_input("New Password", type="password", key="new_password")
        confirm_new_password = c2.text_input("Confirm New Password", type="password", key="confirm_new_password")

        if st.button("Reset Password", type="primary"):
            if len(new_password) < 6:
                st.error("Password must contain at least 6 characters.")
            elif new_password != confirm_new_password:
                st.error("Passwords do not match.")
            else:
                execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_password), username_to_reset))
                st.success(f"Password reset for {username_to_reset}.")

    with tab4:
        users_df = query("""
            SELECT username, full_name, role, COALESCE(is_active,1) AS is_active
            FROM users ORDER BY username
        """)
        selected_user = st.selectbox("Select User", users_df["username"].tolist(), key="activate_user")
        selected_row = users_df[users_df["username"] == selected_user].iloc[0]
        current_status = "Active" if int(selected_row["is_active"]) == 1 else "Inactive"

        st.info(
            f"User: {selected_row['full_name']} | Role: {selected_row['role']} | "
            f"Current Status: {current_status}"
        )

        action = st.radio("Action", ["Activate", "Deactivate"], horizontal=True)

        if selected_user == user["username"] and action == "Deactivate":
            st.warning("You cannot deactivate your own logged-in administrator account.")
        elif st.button("Update User Status", type="primary"):
            execute(
                "UPDATE users SET is_active=? WHERE username=?",
                (1 if action == "Activate" else 0, selected_user)
            )
            st.success(f"{selected_user} updated successfully.")
            st.rerun()

    with tab5:
        st.subheader("Manage Module Access")
        st.caption(
            "By default every user gets the modules their role allows. Turn on custom access "
            "to grant or restrict specific modules for one user — including setting zero modules "
            "if that's intended. Admin-role users always keep Dashboard and User Access, even "
            "with custom access enabled, so an admin can never be locked out of fixing access."
        )
        access_users_df = query("SELECT username, full_name, role FROM users ORDER BY username")
        selected_username = st.selectbox("Select User", access_users_df["username"].tolist(), key="access_user")
        selected_role = access_users_df.loc[access_users_df["username"] == selected_username, "role"].iloc[0]

        current_mode = get_access_mode(selected_username)
        use_custom = st.checkbox(
            "Use custom module access for this user (overrides role default)",
            value=bool(current_mode),
            key="use_custom_access"
        )

        if use_custom:
            if current_mode:
                existing = query("SELECT module FROM user_module_access WHERE username=?", (selected_username,))
                default_selection = sorted(existing["module"].tolist())
            else:
                default_selection = sorted(role_default_modules(selected_role))

            selected_modules = st.multiselect(
                "Modules this user can access (leave empty to block all modules)",
                ALL_MODULES,
                default=default_selection,
                key="access_modules"
            )

            if st.button("Save Module Access", type="primary"):
                with conn() as c:
                    c.execute("DELETE FROM user_module_access WHERE username=?", (selected_username,))
                    c.executemany(
                        "INSERT INTO user_module_access(username,module) VALUES(?,?)",
                        [(selected_username, m) for m in selected_modules]
                    )
                    c.execute(
                        """INSERT INTO user_access_mode(username,use_custom) VALUES(?,1)
                           ON CONFLICT(username) DO UPDATE SET use_custom=1""",
                        (selected_username,)
                    )
                    c.commit()
                if selected_role == "Admin":
                    st.info("Note: Admin role retains Dashboard and User Access regardless of this selection.")
                st.success(f"Custom module access saved for {selected_username}.")
                st.rerun()
        else:
            if current_mode:
                st.warning(f"{selected_username} currently has custom access overrides.")
                if st.button("Revert to Role-Based Access", type="primary"):
                    with conn() as c:
                        c.execute("DELETE FROM user_module_access WHERE username=?", (selected_username,))
                        c.execute("DELETE FROM user_access_mode WHERE username=?", (selected_username,))
                        c.commit()
                    st.success(f"{selected_username} reverted to role-based default access.")
                    st.rerun()
            else:
                st.info(f"{selected_username} is currently using role-based default access ({selected_role}).")

        st.markdown("### Current Access Overrides")
        overrides = query("""
            SELECT uma.username, u.full_name, u.role, uma.module
            FROM user_module_access uma
            JOIN users u ON u.username = uma.username
            JOIN user_access_mode m ON m.username = uma.username AND m.use_custom = 1
            ORDER BY uma.username, uma.module
        """)
        zero_access = query("""
            SELECT m.username, u.full_name, u.role
            FROM user_access_mode m
            JOIN users u ON u.username = m.username
            WHERE m.use_custom = 1
              AND NOT EXISTS (SELECT 1 FROM user_module_access uma WHERE uma.username = m.username)
        """)
        if overrides.empty and zero_access.empty:
            st.info("No users currently have custom module access overrides.")
        else:
            if not overrides.empty:
                st.dataframe(overrides, use_container_width=True, hide_index=True)
            if not zero_access.empty:
                st.warning("These users have custom access enabled with zero modules selected (no access, except forced Admin defaults):")
                st.dataframe(zero_access, use_container_width=True, hide_index=True)

# ---------------- Dashboard ----------------
elif page == "Dashboard":
    st.title("Executive Dashboard")

    total_rooms = scalar("SELECT COUNT(*) FROM rooms")
    occupied = scalar("SELECT COUNT(*) FROM rooms WHERE status='Occupied'")
    available_rooms = scalar("SELECT COUNT(*) FROM rooms WHERE status='Available'")
    reserved_rooms = scalar("SELECT COUNT(*) FROM rooms WHERE status='Reserved'")
    maintenance_rooms = scalar("SELECT COUNT(*) FROM rooms WHERE status IN ('Maintenance','Out of Service')")
    occupancy = occupied / total_rooms * 100 if total_rooms else 0

    room_revenue = scalar("""
        SELECT SUM(MAX(julianday(checkout_date)-julianday(checkin_date),1) * room_rate)
        FROM reservations WHERE status IN ('Checked-in','Checked-out')
    """)
    restaurant_sales = scalar("SELECT SUM(amount) FROM orders")
    collections = scalar("SELECT SUM(amount) FROM payments")
    expenses = scalar("SELECT SUM(amount) FROM expenses")
    open_kot = scalar("SELECT COUNT(DISTINCT kot_no) FROM orders WHERE status NOT IN ('Served','Cancelled')")
    checkins_today = scalar("SELECT COUNT(*) FROM reservations WHERE checkin_date=date('now')")
    checkouts_today = scalar("SELECT COUNT(*) FROM reservations WHERE checkout_date=date('now')")
    inhouse_guests = scalar("SELECT COALESCE(SUM(adults+children),0) FROM reservations WHERE status='Checked-in'")
    avg_daily_rate = scalar("SELECT AVG(room_rate) FROM reservations WHERE status IN ('Checked-in','Checked-out')")
    revpar = float(room_revenue or 0) / total_rooms if total_rooms else 0
    outstanding_bills = max(float(room_revenue or 0)+float(restaurant_sales or 0)-float(collections or 0),0)
    open_maintenance = scalar("SELECT COUNT(*) FROM maintenance WHERE status!='Closed'")
    delayed_kitchen = scalar("SELECT COUNT(DISTINCT kot_no) FROM orders WHERE status IN ('New','Preparing') AND (julianday('now')-julianday(order_time))*1440 > target_minutes")
    pending_approvals = scalar("SELECT COUNT(*) FROM approval_requests WHERE status='Pending'")
    low_stock = int((stock_df()["stock_status"]=="REORDER").sum())

    st.markdown(
        f"""<div class='exec-strip'>
        <div><div class='exec-strip-title'>Good day, {user['full_name']}</div>
        <div class='exec-strip-copy'>Live command center for hotel operations, revenue, service and controls.</div></div>
        <div class='exec-chip'>Business Date • {date.today().strftime('%d %b %Y')}</div>
        </div>""", unsafe_allow_html=True
    )

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Occupancy",f"{occupancy:.1f}%",f"{occupied}/{total_rooms} rooms")
    k2.metric("Revenue",money(float(room_revenue or 0)+float(restaurant_sales or 0)),f"ADR {money(avg_daily_rate)}")
    k3.metric("Arrivals Today",int(checkins_today),f"{int(checkouts_today)} departures")
    k4.metric("In-house Guests",int(inhouse_guests),f"RevPAR {money(revpar)}")
    k5.metric("Net Cash",money(float(collections or 0)-float(expenses or 0)))

    k6,k7,k8,k9,k10 = st.columns(5)
    k6.metric("Available Rooms",int(available_rooms),f"{int(reserved_rooms)} reserved")
    k7.metric("Restaurant Sales",money(restaurant_sales),f"{int(open_kot)} open KOT")
    k8.metric("Outstanding Bills",money(outstanding_bills))
    k9.metric("Pending Approvals",int(pending_approvals))
    k10.metric("Maintenance",int(open_maintenance),f"{int(maintenance_rooms)} rooms affected")

    st.markdown("<div class='exec-section-label'>Quick Actions</div>",unsafe_allow_html=True)
    def _go(target):
        st.session_state["nav_page"] = target
    qa1,qa2,qa3,qa4,qa5,qa6 = st.columns(6)
    qa1.button("➕ Reservation",use_container_width=True,on_click=_go,args=("Reservations",))
    qa2.button("🛎️ Check In / Out",use_container_width=True,on_click=_go,args=("Front Desk",))
    qa3.button("🍽️ New Order",use_container_width=True,on_click=_go,args=("Restaurant POS",))
    qa4.button("📦 Inventory",use_container_width=True,on_click=_go,args=("Inventory",))
    qa5.button("🛒 Purchase Order",use_container_width=True,on_click=_go,args=("Purchasing",))
    qa6.button("📑 Reports",use_container_width=True,on_click=_go,args=("Reports",))

    left,right = st.columns([1.55,1])
    with left:
        st.subheader("30-Day Revenue Trend")
        room_trend=query("""
            SELECT checkin_date day, SUM(MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate) room_revenue
            FROM reservations WHERE checkin_date>=date('now','-29 day') GROUP BY checkin_date ORDER BY checkin_date
        """)
        rest_trend=query("""
            SELECT substr(order_time,1,10) day, SUM(amount) restaurant_sales
            FROM orders WHERE substr(order_time,1,10)>=date('now','-29 day') GROUP BY substr(order_time,1,10) ORDER BY day
        """)
        trend=pd.DataFrame({"day":pd.date_range(end=date.today(),periods=30).strftime("%Y-%m-%d")})
        trend=trend.merge(room_trend,on="day",how="left").merge(rest_trend,on="day",how="left").fillna(0)
        st.line_chart(trend.set_index("day"),height=320)

        c1,c2=st.columns(2)
        with c1:
            st.subheader("Room Status")
            room_status=query("SELECT status,COUNT(*) rooms FROM rooms GROUP BY status ORDER BY rooms DESC")
            st.bar_chart(room_status.set_index("status"),height=255) if not room_status.empty else st.info("No room data.")
        with c2:
            st.subheader("Payment Mix")
            payment_mix=query("SELECT payment_method,SUM(amount) amount FROM payments GROUP BY payment_method ORDER BY amount DESC")
            st.bar_chart(payment_mix.set_index("payment_method"),height=255) if not payment_mix.empty else st.info("No payment data.")

    with right:
        st.subheader("Executive Insights")
        revenue_total=float(room_revenue or 0)+float(restaurant_sales or 0)
        st.markdown(f"<div class='insight-card'><strong>Revenue Position</strong><div>Total recorded revenue is {money(revenue_total)}. Outstanding guest and restaurant bills are {money(outstanding_bills)}.</div></div>",unsafe_allow_html=True)
        st.markdown(f"<div class='insight-card'><strong>Room Performance</strong><div>Occupancy is {occupancy:.1f}% with {int(available_rooms)} rooms available and {int(reserved_rooms)} reserved.</div></div>",unsafe_allow_html=True)
        st.markdown(f"<div class='insight-card'><strong>Control Attention</strong><div>{int(pending_approvals)} approval(s), {int(open_maintenance)} maintenance ticket(s), and {low_stock} low-stock item(s) require review.</div></div>",unsafe_allow_html=True)

        st.subheader("Live Alerts")
        if delayed_kitchen:
            st.markdown(f"<div class='alert-card red'><div class='alert-title'>⏱️ Kitchen SLA breach</div><div class='alert-copy'>{int(delayed_kitchen)} KOT(s) exceeded target preparation time.</div></div>",unsafe_allow_html=True)
        if pending_approvals:
            st.markdown(f"<div class='alert-card blue'><div class='alert-title'>✅ Approval queue</div><div class='alert-copy'>{int(pending_approvals)} request(s) await action.</div></div>",unsafe_allow_html=True)
        if open_maintenance:
            st.markdown(f"<div class='alert-card red'><div class='alert-title'>🛠️ Maintenance</div><div class='alert-copy'>{int(open_maintenance)} ticket(s) remain open.</div></div>",unsafe_allow_html=True)
        if low_stock:
            st.markdown(f"<div class='alert-card'><div class='alert-title'>📦 Reorder alert</div><div class='alert-copy'>{low_stock} inventory item(s) are at or below reorder level.</div></div>",unsafe_allow_html=True)
        if not any([delayed_kitchen,pending_approvals,open_maintenance,low_stock]):
            st.markdown("<div class='alert-card green'><div class='alert-title'>✅ Operations healthy</div><div class='alert-copy'>No critical operational alerts are open.</div></div>",unsafe_allow_html=True)

    st.subheader("Today's Operations")
    arrivals=query("""
        SELECT reservation_id,guest_name,room_no,checkin_date,checkout_date,status,source
        FROM reservations WHERE checkin_date=date('now') OR checkout_date=date('now')
        ORDER BY checkin_date,room_no
    """)
    room_ops=query("SELECT room_no,room_type,status,housekeeping,rate FROM rooms ORDER BY room_no")
    t1,t2=st.tabs(["Arrivals & Departures","Room Operations"])
    with t1:
        st.dataframe(arrivals,use_container_width=True,hide_index=True,height=280)
    with t2:
        st.dataframe(room_ops,use_container_width=True,hide_index=True,height=320)

# ---------------- Reservations ----------------
elif page == "Reservations":
    st.title("Reservations & Guest Booking")
    st.caption("Create reservations, review upcoming stays and export the booking register.")

    reservations = query("SELECT * FROM reservations ORDER BY created_at DESC")
    today_str = str(date.today())
    arrivals_today = int((reservations["checkin_date"] == today_str).sum()) if not reservations.empty else 0
    departures_today = int((reservations["checkout_date"] == today_str).sum()) if not reservations.empty else 0
    confirmed = int((reservations["status"] == "Reserved").sum()) if not reservations.empty else 0
    in_house = int((reservations["status"] == "Checked-in").sum()) if not reservations.empty else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Confirmed Bookings", confirmed)
    c2.metric("Arrivals Today", arrivals_today)
    c3.metric("Departures Today", departures_today)
    c4.metric("In-house Guests", in_house)

    create_tab, register_tab = st.tabs(["➕ New Reservation", "📋 Reservation Register"])

    with create_tab:
        available = query("SELECT room_no, room_type, rate FROM rooms WHERE status='Available' ORDER BY room_no")
        if available.empty:
            st.warning("No rooms are currently marked as available.")
        with st.form("reservation_enterprise"):
            st.subheader("Guest Information")
            c1,c2,c3 = st.columns(3)
            guest = c1.text_input("Guest Name *")
            mobile = c2.text_input("Mobile Number")
            id_no = c3.text_input("Passport / National ID")

            st.subheader("Stay Details")
            c1,c2,c3 = st.columns(3)
            room_options = available["room_no"].astype(str).tolist() if not available.empty else ["No room"]
            room = c1.selectbox("Room *", room_options)
            checkin = c2.date_input("Check-in Date", date.today())
            checkout = c3.date_input("Check-out Date", date.today()+timedelta(days=1))

            selected = available[available["room_no"].astype(str)==str(room)] if not available.empty else pd.DataFrame()
            default_rate = float(selected["rate"].iloc[0]) if not selected.empty else 0.0
            room_type = str(selected["room_type"].iloc[0]) if not selected.empty else "N/A"

            c1,c2,c3,c4 = st.columns(4)
            adults = c1.number_input("Adults", min_value=1, max_value=10, value=1)
            children = c2.number_input("Children", min_value=0, max_value=10, value=0)
            rate = c3.number_input("Nightly Rate", min_value=0.0, value=default_rate, step=50.0)
            deposit = c4.number_input("Advance Deposit", min_value=0.0, value=0.0, step=50.0)

            c1,c2 = st.columns(2)
            source = c1.selectbox("Booking Source",["Walk-in","Direct","Website","Corporate","Travel Agent","OTA"])
            c2.text_input("Room Type", value=room_type, disabled=True)

            nights=max((checkout-checkin).days,0)
            estimated_total=nights*rate
            st.info(f"Estimated stay: {nights} night(s) • Room amount: {money(estimated_total)} • Estimated balance: {money(max(estimated_total-deposit,0))}")
            save = st.form_submit_button("Create Reservation", type="primary", use_container_width=True)

        if save:
            if not guest.strip():
                st.error("Guest name is required.")
            elif room=="No room":
                st.error("An available room is required.")
            elif checkout<=checkin:
                st.error("Check-out date must be after check-in date.")
            else:
                rid = next_code("RSV","reservations")
                execute("""INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (rid,guest.strip(),mobile.strip(),id_no.strip(),room,str(checkin),str(checkout),adults,children,
                         "Reserved",rate,deposit,source,datetime.now().isoformat(timespec="seconds")))
                execute("UPDATE rooms SET status='Reserved' WHERE room_no=?",(room,))
                st.success(f"Reservation {rid} created successfully for {guest.strip()}.")
                st.rerun()

    with register_tab:
        st.subheader("Search Reservations")
        f1,f2,f3,f4 = st.columns(4)
        search_text = f1.text_input("Guest / Mobile / ID / Reservation")
        status_values = ["All"] + sorted(reservations["status"].dropna().astype(str).unique().tolist()) if not reservations.empty else ["All"]
        status_filter = f2.selectbox("Status", status_values)
        from_date = f3.date_input("Check-in From", date.today()-timedelta(days=30), key="reservation_from")
        to_date = f4.date_input("Check-in To", date.today()+timedelta(days=180), key="reservation_to")

        filtered=reservations.copy()
        if not filtered.empty:
            dt=pd.to_datetime(filtered["checkin_date"],errors="coerce")
            filtered=filtered[(dt>=pd.Timestamp(from_date)) & (dt<=pd.Timestamp(to_date))]
            if status_filter!="All":
                filtered=filtered[filtered["status"]==status_filter]
            if search_text.strip():
                needle=search_text.strip().lower()
                cols=["reservation_id","guest_name","mobile","id_number","room_no"]
                mask=pd.Series(False,index=filtered.index)
                for col in cols:
                    if col in filtered.columns:
                        mask = mask | filtered[col].fillna("").astype(str).str.lower().str.contains(needle,regex=False)
                filtered=filtered[mask]

        st.dataframe(style_status_column(filtered),use_container_width=True,hide_index=True,height=430)
        st.download_button(
            "Download Reservation Register",
            data=excel_file({"Reservations":filtered}),
            file_name=f"Reservation_Register_{from_date}_{to_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# ---------------- Front Desk ----------------
elif page == "Front Desk":
    st.title("Front Desk Operations")
    st.caption("Manage arrivals, room transfers, guest folios and departures.")

    reserved_df=query("SELECT * FROM reservations WHERE status='Reserved' ORDER BY checkin_date, room_no")
    checked_df=query("SELECT * FROM reservations WHERE status='Checked-in' ORDER BY room_no")
    available_df=query("SELECT room_no, room_type, rate, housekeeping FROM rooms WHERE status='Available' ORDER BY room_no")

    today_str=str(date.today())
    today_arrivals=int((reserved_df["checkin_date"]==today_str).sum()) if not reserved_df.empty else 0
    overdue_arrivals=int((pd.to_datetime(reserved_df["checkin_date"],errors="coerce")<pd.Timestamp(date.today())).sum()) if not reserved_df.empty else 0
    today_departures=int((checked_df["checkout_date"]==today_str).sum()) if not checked_df.empty else 0

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Pending Arrivals",len(reserved_df),f"{today_arrivals} today")
    c2.metric("In-house Stays",len(checked_df))
    c3.metric("Departures Today",today_departures)
    c4.metric("Overdue Arrivals",overdue_arrivals)

    t1,t2,t3,t4=st.tabs(["🛎️ Check-in","🔁 Room Transfer","🧾 Guest Folio","✅ Check-out"])

    with t1:
        if reserved_df.empty:
            st.info("No pending reservations are available for check-in.")
        else:
            labels={r["reservation_id"]:f'{r["reservation_id"]} | {r["guest_name"]} | Room {r["room_no"]} | {r["checkin_date"]}' for _,r in reserved_df.iterrows()}
            rid=st.selectbox("Select Arrival",reserved_df["reservation_id"].tolist(),format_func=lambda x:labels.get(x,x))
            row=reserved_df[reserved_df["reservation_id"]==rid].iloc[0]
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Guest",str(row["guest_name"]))
            c2.metric("Room",str(row["room_no"]))
            c3.metric("Arrival",str(row["checkin_date"]))
            c4.metric("Deposit",money(row["deposit"]))
            verify=st.checkbox("Guest identity and reservation details verified")
            if st.button("Check-in Guest",type="primary",disabled=not verify,use_container_width=True):
                room=str(row["room_no"])
                hk=scalar("SELECT housekeeping FROM rooms WHERE room_no=?",(room,),"Unknown")
                if str(hk).lower() not in {"clean","ready"}:
                    st.error(f"Room {room} is not ready. Housekeeping status: {hk}")
                else:
                    execute("UPDATE reservations SET status='Checked-in' WHERE reservation_id=?",(rid,))
                    execute("UPDATE rooms SET status='Occupied' WHERE room_no=?",(room,))
                    st.success(f"{row['guest_name']} checked in to room {room}.")
                    st.rerun()

    with t2:
        if checked_df.empty or available_df.empty:
            st.info("A checked-in guest and an available room are required for room transfer.")
        else:
            labels={r["reservation_id"]:f'{r["guest_name"]} | Current Room {r["room_no"]}' for _,r in checked_df.iterrows()}
            rid=st.selectbox("Guest",checked_df["reservation_id"].tolist(),key="transfer_rid",format_func=lambda x:labels.get(x,x))
            new_room=st.selectbox("Transfer To",available_df["room_no"].astype(str).tolist())
            reason=st.text_area("Transfer Reason",placeholder="Example: guest preference, maintenance issue, upgrade")
            if st.button("Confirm Room Transfer",type="primary",use_container_width=True):
                old_room=str(checked_df.loc[checked_df["reservation_id"]==rid,"room_no"].iloc[0])
                execute("UPDATE reservations SET room_no=? WHERE reservation_id=?",(new_room,rid))
                execute("UPDATE rooms SET status='Available', housekeeping='Dirty' WHERE room_no=?",(old_room,))
                execute("UPDATE rooms SET status='Occupied' WHERE room_no=?",(new_room,))
                st.success(f"Guest transferred from room {old_room} to room {new_room}. Reason: {reason or 'Not specified'}")
                st.rerun()

    with t3:
        if checked_df.empty:
            st.info("No checked-in guests are available.")
        else:
            labels={r["reservation_id"]:f'{r["guest_name"]} | Room {r["room_no"]}' for _,r in checked_df.iterrows()}
            rid=st.selectbox("Guest Folio",checked_df["reservation_id"].tolist(),key="folio_rid",format_func=lambda x:labels.get(x,x))
            row=checked_df[checked_df["reservation_id"]==rid].iloc[0]
            nights=max((pd.to_datetime(row["checkout_date"])-pd.to_datetime(row["checkin_date"])).days,1)
            room_charge=nights*float(row["room_rate"])
            room_orders=query("SELECT order_id,order_time,status,amount FROM orders WHERE order_type='Room Service' AND table_room=? ORDER BY order_time",(str(row["room_no"]),))
            food=float(room_orders["amount"].sum()) if not room_orders.empty else 0.0
            paid=scalar("SELECT SUM(amount) FROM payments WHERE reference=?",(rid,))
            deposit=float(row["deposit"] or 0)
            gross=room_charge+food
            balance=gross-deposit-paid
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Room Charges",money(room_charge))
            c2.metric("Room Service",money(food))
            c3.metric("Deposit",money(deposit))
            c4.metric("Other Payments",money(paid))
            c5.metric("Balance",money(balance))
            st.dataframe(room_orders,use_container_width=True,hide_index=True,height=260)

    with t4:
        if checked_df.empty:
            st.info("No checked-in guests are available for checkout.")
        else:
            labels={r["reservation_id"]:f'{r["guest_name"]} | Room {r["room_no"]} | Due {r["checkout_date"]}' for _,r in checked_df.iterrows()}
            rid=st.selectbox("Select Departure",checked_df["reservation_id"].tolist(),key="checkout_rid",format_func=lambda x:labels.get(x,x))
            row=checked_df[checked_df["reservation_id"]==rid].iloc[0]
            nights=max((pd.to_datetime(row["checkout_date"])-pd.to_datetime(row["checkin_date"])).days,1)
            room_charge=nights*float(row["room_rate"])
            food=scalar("SELECT SUM(amount) FROM orders WHERE order_type='Room Service' AND table_room=?",(str(row["room_no"]),))
            prior_payments=scalar("SELECT SUM(amount) FROM payments WHERE reference=?",(rid,))
            balance=room_charge+food-float(row["deposit"])-prior_payments
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Nights",nights)
            c2.metric("Room",money(room_charge))
            c3.metric("Food",money(food))
            c4.metric("Deposit/Paid",money(float(row["deposit"])+prior_payments))
            c5.metric("Final Balance",money(balance))
            method=st.selectbox("Settlement Method",["Cash","MADA","Visa","MasterCard","Bank Transfer","Corporate Credit"])
            checkout_note=st.text_area("Checkout Note",placeholder="Optional remarks")
            confirm=st.checkbox("Final folio reviewed and payment confirmed")
            if st.button("Complete Checkout",type="primary",disabled=not confirm,use_container_width=True):
                if balance>0:
                    pid=next_code("PAY","payments")
                    execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?)",
                            (pid,datetime.now().isoformat(timespec="seconds"),rid,row["guest_name"],method,balance,"Hotel Checkout"))
                execute("UPDATE reservations SET status='Checked-out' WHERE reservation_id=?",(rid,))
                execute("UPDATE rooms SET status='Available', housekeeping='Dirty' WHERE room_no=?",(str(row["room_no"]),))
                st.success(f"Checkout completed for {row['guest_name']}. {checkout_note}")
                st.rerun()

# ---------------- Rooms ----------------
elif page == "Rooms":
    st.title("Room Control Board")
    st.caption("Live view of room availability, occupancy and housekeeping readiness.")
    rooms=query("SELECT * FROM rooms ORDER BY room_no")
    if rooms.empty:
        st.info("No room master data found.")
    else:
        total=len(rooms)
        available=int((rooms["status"]=="Available").sum())
        occupied=int((rooms["status"]=="Occupied").sum())
        reserved=int((rooms["status"]=="Reserved").sum())
        dirty=int((rooms["housekeeping"]=="Dirty").sum())
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Total Rooms",total)
        c2.metric("Available",available)
        c3.metric("Occupied",occupied)
        c4.metric("Reserved",reserved)
        c5.metric("Dirty Rooms",dirty)

        f1,f2,f3=st.columns(3)
        status_opts=["All"]+sorted(rooms["status"].dropna().astype(str).unique().tolist())
        hk_opts=["All"]+sorted(rooms["housekeeping"].dropna().astype(str).unique().tolist())
        type_opts=["All"]+sorted(rooms["room_type"].dropna().astype(str).unique().tolist())
        status_filter=f1.selectbox("Room Status",status_opts)
        hk_filter=f2.selectbox("Housekeeping",hk_opts)
        type_filter=f3.selectbox("Room Type",type_opts)
        filtered=rooms.copy()
        if status_filter!="All": filtered=filtered[filtered["status"]==status_filter]
        if hk_filter!="All": filtered=filtered[filtered["housekeeping"]==hk_filter]
        if type_filter!="All": filtered=filtered[filtered["room_type"]==type_filter]
        st.dataframe(filtered,use_container_width=True,hide_index=True,height=500)
        st.download_button("Download Room Status",data=excel_file({"Rooms":filtered}),file_name=f"Room_Status_{date.today()}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

# ---------------- Restaurant POS ----------------
elif page == "Restaurant POS":
    st.title("Restaurant Control Tower")
    st.markdown("<div class='demo-banner'>Live restaurant operations • POS • Table control • Kitchen queue • Settlement</div>", unsafe_allow_html=True)

    menu=query("SELECT * FROM menu ORDER BY category,item_name")
    orders_today=query("SELECT * FROM orders WHERE date(order_time)=date('now','localtime')")
    open_orders=orders_today[~orders_today["status"].isin(["Served","Cancelled"])] if not orders_today.empty else orders_today
    paid_today=orders_today[orders_today["payment_status"]=="Paid"] if not orders_today.empty else orders_today
    gross_sales=float(orders_today.loc[orders_today["status"]!="Cancelled","amount"].sum()) if not orders_today.empty else 0.0
    order_count=int(orders_today.loc[orders_today["status"]!="Cancelled","kot_no"].nunique()) if not orders_today.empty else 0
    avg_bill=(gross_sales/order_count) if order_count else 0.0
    pending_kitchen=int(open_orders["kot_no"].nunique()) if not open_orders.empty else 0
    cancelled=int(orders_today.loc[orders_today["status"]=="Cancelled","kot_no"].nunique()) if not orders_today.empty else 0

    k1,k2,k3,k4,k5,k6=st.columns(6)
    k1.metric("Today's Sales",money(gross_sales))
    k2.metric("Orders",order_count)
    k3.metric("Average Bill",money(avg_bill))
    k4.metric("Kitchen Queue",pending_kitchen)
    k5.metric("Paid KOTs",int(paid_today["kot_no"].nunique()) if not paid_today.empty else 0)
    k6.metric("Cancelled",cancelled)

    pos_tab,tables_tab,settlement_tab,history_tab=st.tabs(["New Order","Table Map","Settlement","Order History"])

    if "pos_cart" not in st.session_state:
        st.session_state.pos_cart=[]

    with pos_tab:
        left,center,right=st.columns([1.05,1.65,1.25],gap="large")
        with left:
            st.markdown("<div class='enterprise-section-title'>Order Details</div>",unsafe_allow_html=True)
            order_type=st.selectbox("Order Type",["Dine-in","Takeaway","Room Service"],key="pos_order_type")
            checked=query("SELECT room_no,guest_name FROM reservations WHERE status='Checked-in' ORDER BY CAST(room_no AS INTEGER)")
            if order_type=="Room Service":
                if checked.empty:
                    location=st.selectbox("Room No",["No checked-in rooms"])
                    guest=""
                    st.warning("No checked-in rooms available.")
                else:
                    location=st.selectbox("Room No",checked["room_no"].astype(str).tolist())
                    guest=str(checked.loc[checked["room_no"].astype(str)==str(location),"guest_name"].iloc[0])
                    st.text_input("Guest Name",value=guest,disabled=True)
            elif order_type=="Dine-in":
                location=st.selectbox("Table No",[f"T{i:02d}" for i in range(1,21)])
                guest=st.text_input("Guest / Reference",value="Walk-in")
            else:
                location=st.text_input("Takeaway Reference",value=f"TA-{datetime.now().strftime('%H%M')}")
                guest=st.text_input("Customer Name",value="Walk-in")
            priority=st.selectbox("Priority",["Normal","High","VIP"])
            chef=st.selectbox("Chef",["Unassigned","Chef Ahmed","Chef Kumar","Chef Maria"])
            instructions=st.text_area("Order Instructions",height=90)

        with center:
            st.markdown("<div class='enterprise-section-title'>Menu</div>",unsafe_allow_html=True)
            search_term=st.text_input("Search menu item",placeholder="Type item name...")
            categories=["All"]+sorted(menu["category"].dropna().astype(str).unique().tolist()) if not menu.empty else ["All"]
            category=st.radio("Category",categories,horizontal=True)
            filtered_menu=menu.copy()
            if category!="All": filtered_menu=filtered_menu[filtered_menu["category"]==category]
            if search_term.strip(): filtered_menu=filtered_menu[filtered_menu["item_name"].str.contains(search_term.strip(),case=False,na=False)]
            if filtered_menu.empty:
                st.info("No menu items match the selected filters.")
            else:
                cols=st.columns(3)
                for idx,row in filtered_menu.reset_index(drop=True).iterrows():
                    with cols[idx%3]:
                        st.markdown(f"**{row['item_name']}**")
                        st.caption(f"{row['category']} • {row['station']}")
                        st.write(money(row['price']))
                        if st.button("Add",key=f"add_{row['item_code']}_{idx}",use_container_width=True):
                            st.session_state.pos_cart.append({
                                "item_code":str(row["item_code"]),"item_name":str(row["item_name"]),
                                "qty":1.0,"rate":float(row["price"]),"amount":float(row["price"]),
                                "station":str(row["station"]),"chef":chef,"priority":priority,
                                "instructions":instructions,"target_minutes":int(row["target_minutes"]),
                                "ingredient":str(row["ingredient"] or ""),"qty_per_item":float(row["qty_per_item"] or 0)
                            })
                            st.rerun()

        with right:
            st.markdown("<div class='enterprise-section-title'>Current Order</div>",unsafe_allow_html=True)
            if not st.session_state.pos_cart:
                st.info("Select menu items to build the order.")
            else:
                cart_df=pd.DataFrame(st.session_state.pos_cart)
                for i,line in cart_df.iterrows():
                    c1,c2=st.columns([3,1])
                    c1.write(f"**{line['item_name']}**  × {line['qty']:g}")
                    c1.caption(f"{money(line['amount'])} • {line['station']}")
                    if c2.button("✕",key=f"remove_cart_{i}"):
                        st.session_state.pos_cart.pop(i); st.rerun()
                subtotal=float(cart_df["amount"].sum())
                discount_pct=st.number_input("Discount %",0.0,100.0,0.0,0.5)
                discount=subtotal*discount_pct/100
                taxable=subtotal-discount
                vat=taxable*0.15
                grand_total=taxable+vat
                st.divider()
                st.write(f"Subtotal: **{money(subtotal)}**")
                st.write(f"Discount: **{money(discount)}**")
                st.write(f"VAT 15%: **{money(vat)}**")
                st.markdown(f"### Total: {money(grand_total)}")
                b1,b2=st.columns(2)
                if b1.button("Clear",use_container_width=True): st.session_state.pos_cart=[]; st.rerun()
                send=b2.button("Send KOT",type="primary",use_container_width=True)
                if send:
                    if order_type=="Room Service" and location=="No checked-in rooms":
                        st.error("No checked-in room is available.")
                    else:
                        kot=next_code("KOT","orders")
                        order_time=datetime.now().isoformat(timespec="seconds")
                        payment_status="Room Charge" if order_type=="Room Service" else "Pending"
                        # Store discount proportionally in line rates so existing finance logic remains compatible.
                        multiplier=(1-discount_pct/100)
                        for line in st.session_state.pos_cart:
                            oid=next_code("ORD","orders")
                            adjusted_rate=float(line["rate"])*multiplier*1.15
                            adjusted_amount=float(line["qty"])*adjusted_rate
                            execute("""INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (oid,kot,order_time,order_type,str(location),guest,line["item_code"],line["item_name"],
                                     line["qty"],adjusted_rate,adjusted_amount,line["station"],line["chef"],line["priority"],
                                     line["instructions"],line["target_minutes"],"","","","New",payment_status))
                            if line["ingredient"] and line["qty_per_item"]>0:
                                execute("UPDATE inventory SET issued_qty=issued_qty+? WHERE item_name=?",
                                        (line["qty"]*line["qty_per_item"],line["ingredient"]))
                        st.session_state.pos_cart=[]
                        st.success(f"{kot} sent to kitchen. Total {money(grand_total)}")
                        st.rerun()

    with tables_tab:
        st.markdown("<div class='enterprise-section-title'>Live Floor View</div>",unsafe_allow_html=True)
        active=query("SELECT table_room,kot_no,MIN(order_time) order_time,SUM(amount) amount,MAX(status) status FROM orders WHERE order_type='Dine-in' AND status NOT IN ('Served','Cancelled') GROUP BY table_room,kot_no")
        active_map={str(r['table_room']):r for _,r in active.iterrows()} if not active.empty else {}
        for row_start in range(1,21,5):
            cols=st.columns(5)
            for j,table_no in enumerate(range(row_start,min(row_start+5,21))):
                label=f"T{table_no:02d}"
                with cols[j]:
                    if label in active_map:
                        r=active_map[label]
                        elapsed=int((datetime.now()-pd.to_datetime(r['order_time']).to_pydatetime()).total_seconds()/60)
                        st.error(f"**{label} • OCCUPIED**\n\n{r['kot_no']} • {money(r['amount'])}\n\n{elapsed} min")
                    else:
                        st.success(f"**{label} • AVAILABLE**")

    with settlement_tab:
        unpaid=query("SELECT * FROM orders WHERE payment_status='Pending' AND status!='Cancelled' ORDER BY order_time DESC")
        if unpaid.empty:
            st.success("No pending restaurant settlements.")
        else:
            summary=unpaid.groupby(["kot_no","order_time","order_type","table_room","guest_ref"],as_index=False)["amount"].sum()
            st.dataframe(summary,use_container_width=True,hide_index=True)
            selected_kots=st.multiselect("Select KOTs",summary["kot_no"].tolist())
            method=st.selectbox("Payment Method",["Cash","MADA","Visa","MasterCard","AMEX","Apple Pay","STC Pay"])
            if selected_kots:
                due=float(unpaid[unpaid["kot_no"].isin(selected_kots)]["amount"].sum())
                st.metric("Amount Due",money(due))
                if st.button("Receive Payment",type="primary"):
                    pid=next_code("PAY","payments")
                    execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?)",
                            (pid,datetime.now().isoformat(timespec="seconds"),",".join(selected_kots),"Restaurant",method,due,"Restaurant Sale"))
                    for kot_no in selected_kots: execute("UPDATE orders SET payment_status='Paid' WHERE kot_no=?",(kot_no,))
                    st.success("Payment received successfully."); st.rerun()

    with history_tab:
        h1,h2,h3=st.columns(3)
        hist_from=h1.date_input("From",date.today()-timedelta(days=7),key="rest_hist_from")
        hist_to=h2.date_input("To",date.today(),key="rest_hist_to")
        hist_status=h3.selectbox("Status",["All","New","Preparing","Ready","Served","Cancelled"])
        history=date_range_filter(query("SELECT * FROM orders ORDER BY order_time DESC"),"order_time",hist_from,hist_to)
        if hist_status!="All": history=history[history["status"]==hist_status]
        st.dataframe(history,use_container_width=True,hide_index=True,height=420)
        st.download_button("Export Restaurant Orders",data=excel_file({"Restaurant Orders":history}),file_name=f"Restaurant_Orders_{hist_from}_{hist_to}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- Kitchen ----------------
elif page == "Kitchen Display":
    st.title("Kitchen Display System")
    st.markdown("<div class='demo-banner'>Live KOT queue ordered by priority and waiting time.</div>",unsafe_allow_html=True)
    df=query("""
        SELECT *,CAST((julianday('now','localtime')-julianday(order_time))*1440 AS INTEGER) elapsed_minutes
        FROM orders WHERE status NOT IN ('Served','Cancelled')
        ORDER BY CASE priority WHEN 'VIP' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,order_time
    """)
    if df.empty:
        st.success("Kitchen queue is clear.")
    else:
        df["delay_status"]=df.apply(lambda r:"Delayed" if r["elapsed_minutes"]>r["target_minutes"] and r["status"]!="Ready" else "On Time",axis=1)
        k1,k2,k3,k4=st.columns(4)
        k1.metric("Open KOTs",df["kot_no"].nunique())
        k2.metric("Items",len(df))
        k3.metric("Delayed",int((df["delay_status"]=="Delayed").sum()))
        k4.metric("Average Wait",f"{df['elapsed_minutes'].mean():.0f} min")
        for kot_no,kot_df in df.groupby("kot_no",sort=False):
            first=kot_df.iloc[0]
            elapsed=int(kot_df["elapsed_minutes"].max())
            delayed=bool((kot_df["delay_status"]=="Delayed").any())
            with st.expander(f"{'🔴' if delayed else '🟢'} {kot_no} • {first['order_type']} {first['table_room']} • {elapsed} min",expanded=delayed):
                st.dataframe(kot_df[["item_name","qty","station","chef","priority","instructions","status","elapsed_minutes","target_minutes"]],use_container_width=True,hide_index=True)
                c1,c2,c3=st.columns(3)
                new_status=c1.selectbox("Status",["New","Preparing","Ready","Served","Cancelled"],key=f"kds_status_{kot_no}")
                new_chef=c2.selectbox("Chef",["Unassigned","Chef Ahmed","Chef Kumar","Chef Maria"],key=f"kds_chef_{kot_no}")
                if c3.button("Update KOT",key=f"kds_update_{kot_no}",type="primary",use_container_width=True):
                    now=datetime.now().isoformat(timespec="seconds")
                    execute("UPDATE orders SET status=?,chef=? WHERE kot_no=?",(new_status,new_chef,kot_no))
                    if new_status=="Preparing": execute("UPDATE orders SET started_at=? WHERE kot_no=?",(now,kot_no))
                    elif new_status=="Ready": execute("UPDATE orders SET ready_at=? WHERE kot_no=?",(now,kot_no))
                    elif new_status=="Served": execute("UPDATE orders SET served_at=? WHERE kot_no=?",(now,kot_no))
                    st.success(f"{kot_no} updated."); st.rerun()

elif page == "Kitchen Performance":
    st.title("Restaurant & Kitchen Analytics")
    st.markdown("<div class='demo-banner'>Operational performance, sales trends and service-level monitoring.</div>",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    perf_from=c1.date_input("From Date",date.today()-timedelta(days=30),key="kitchen_perf_from")
    perf_to=c2.date_input("To Date",date.today(),key="kitchen_perf_to")
    raw=date_range_filter(query("SELECT * FROM orders"),"order_time",perf_from,perf_to)
    if raw.empty:
        st.info("No restaurant activity in the selected period.")
    else:
        raw["order_time_dt"]=pd.to_datetime(raw["order_time"],errors="coerce")
        raw["ready_at_dt"]=pd.to_datetime(raw["ready_at"],errors="coerce")
        raw["prep_minutes"]=(raw["ready_at_dt"]-raw["order_time_dt"]).dt.total_seconds()/60
        valid=raw[raw["status"]!="Cancelled"]
        total_sales=float(valid["amount"].sum())
        kots=int(valid["kot_no"].nunique())
        avg_prep=float(valid["prep_minutes"].dropna().mean()) if valid["prep_minutes"].notna().any() else 0.0
        delayed=int((valid["prep_minutes"]>valid["target_minutes"]).sum()) if "target_minutes" in valid else 0
        k1,k2,k3,k4=st.columns(4)
        k1.metric("Sales",money(total_sales)); k2.metric("KOTs",kots); k3.metric("Avg Prep",f"{avg_prep:.1f} min"); k4.metric("Delayed Items",delayed)
        a,b=st.columns(2)
        hourly=valid.groupby(valid["order_time_dt"].dt.hour)["amount"].sum().rename_axis("Hour").reset_index()
        a.markdown("#### Hourly Sales")
        a.bar_chart(hourly.set_index("Hour"))
        top_items=valid.groupby("item_name",as_index=False).agg(Qty=("qty","sum"),Sales=("amount","sum")).sort_values("Sales",ascending=False).head(10)
        b.markdown("#### Top Selling Items")
        b.dataframe(top_items,use_container_width=True,hide_index=True)
        station=valid.groupby(["station","chef"],as_index=False).agg(Items=("order_id","count"),Sales=("amount","sum"),Avg_Prep_Min=("prep_minutes","mean")).sort_values("Items",ascending=False)
        st.markdown("#### Station & Chef Performance")
        st.dataframe(station,use_container_width=True,hide_index=True)
        payment=valid.groupby("payment_status",as_index=False)["amount"].sum()
        st.markdown("#### Payment Status Mix")
        st.bar_chart(payment.set_index("payment_status"))
        st.download_button("Export Restaurant Performance",data=excel_file({"Orders":raw,"Top Items":top_items,"Station Performance":station}),file_name=f"Restaurant_Performance_{perf_from}_{perf_to}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- Housekeeping ----------------
elif page == "Housekeeping":
    st.title("Housekeeping Control Tower")
    st.markdown("<div class='demo-banner'>Live room readiness, staff assignment, inspections, maintenance escalation and lost-and-found control.</div>", unsafe_allow_html=True)

    rooms = query("SELECT * FROM rooms ORDER BY CAST(room_no AS INTEGER)")
    tasks = query("SELECT * FROM housekeeping_tasks ORDER BY created_at DESC")
    today_str = str(date.today())
    today_tasks = tasks[tasks["task_date"] == today_str] if not tasks.empty else tasks

    clean_count = int((rooms["housekeeping"] == "Clean").sum()) if not rooms.empty else 0
    dirty_count = int((rooms["housekeeping"] == "Dirty").sum()) if not rooms.empty else 0
    cleaning_count = int((rooms["housekeeping"] == "Cleaning").sum()) if not rooms.empty else 0
    oos_count = int((rooms["housekeeping"] == "Out of Service").sum()) if not rooms.empty else 0
    pending_tasks = int(today_tasks["status"].isin(["Assigned", "In Progress", "Pending Inspection"]).sum()) if not today_tasks.empty else 0
    inspected_today = int((today_tasks["inspection_status"] == "Passed").sum()) if not today_tasks.empty else 0

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Clean Rooms", clean_count)
    k2.metric("Dirty Rooms", dirty_count)
    k3.metric("In Cleaning", cleaning_count)
    k4.metric("Out of Service", oos_count)
    k5.metric("Pending Tasks", pending_tasks)
    k6.metric("Inspected Today", inspected_today)

    board_tab, assign_tab, task_tab, inspect_tab, lost_tab, analytics_tab = st.tabs([
        "Room Status Board", "Assign Tasks", "Task Execution", "Inspection", "Lost & Found", "Analytics"
    ])

    with board_tab:
        st.markdown("#### Live Room Readiness Board")
        f1,f2,f3 = st.columns(3)
        hk_options = ["All"] + sorted(rooms["housekeeping"].dropna().unique().tolist()) if not rooms.empty else ["All"]
        room_options = ["All"] + sorted(rooms["room_type"].dropna().unique().tolist()) if not rooms.empty else ["All"]
        hk_filter = f1.selectbox("Housekeeping Status", hk_options, key="hk_board_status")
        type_filter = f2.selectbox("Room Type", room_options, key="hk_board_type")
        search_room = f3.text_input("Search Room", key="hk_board_search")

        board = rooms.copy()
        if hk_filter != "All": board = board[board["housekeeping"] == hk_filter]
        if type_filter != "All": board = board[board["room_type"] == type_filter]
        if search_room.strip(): board = board[board["room_no"].astype(str).str.contains(search_room.strip(), regex=False)]

        if board.empty:
            st.info("No rooms match the selected filters.")
        else:
            cols = st.columns(5)
            for idx, row in board.reset_index(drop=True).iterrows():
                hk = str(row["housekeeping"])
                room_state = str(row["status"])
                cls = "green" if hk in {"Clean", "Inspected"} else "amber" if hk in {"Cleaning"} else "red" if hk in {"Dirty", "Out of Service"} else ""
                with cols[idx % 5]:
                    st.markdown(
                        f"""<div class='enterprise-card' style='min-height:155px;margin-bottom:12px;'>
                        <div style='font-size:1.35rem;font-weight:900;'>Room {row['room_no']}</div>
                        <div style='color:#64748b;margin:.2rem 0 .7rem;'>{row['room_type']} • {money(row['rate'])}</div>
                        <span class='enterprise-badge {cls}'>{hk}</span>
                        <div style='margin-top:.65rem;font-size:.82rem;color:#475569;'>Front Office: <b>{room_state}</b></div>
                        </div>""", unsafe_allow_html=True
                    )

        st.download_button(
            "Export Room Status",
            data=excel_file({"Room Status": board}),
            file_name=f"Housekeeping_Room_Status_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with assign_tab:
        st.markdown("#### Create Housekeeping Assignment")
        with st.form("housekeeping_assignment", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            selected_room = c1.selectbox("Room", rooms["room_no"].tolist() if not rooms.empty else [])
            task_type = c2.selectbox("Task Type", ["Checkout Cleaning", "Stayover Service", "Deep Cleaning", "Turndown Service", "Inspection Rework", "Public Area Support"])
            priority = c3.selectbox("Priority", ["Normal", "High", "Urgent"])
            c1,c2,c3 = st.columns(3)
            assigned_to = c1.selectbox("Assign To", ["HK Team A", "HK Team B", "HK Team C", "Supervisor", "Unassigned"])
            task_date = c2.date_input("Task Date", date.today(), key="hk_task_date")
            initial_status = c3.selectbox("Initial Status", ["Assigned", "In Progress"])
            notes = st.text_area("Instructions / Guest Preferences")
            submit_task = st.form_submit_button("Create Assignment", type="primary")
        if submit_task:
            task_id = next_code("HKT", "housekeeping_tasks", "task_id")
            now = datetime.now().isoformat(timespec="seconds")
            execute("""INSERT INTO housekeeping_tasks(
                task_id,task_date,room_no,task_type,priority,assigned_to,status,start_time,
                completed_time,inspected_by,inspection_status,notes,created_by,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id,str(task_date),selected_room,task_type,priority,assigned_to,initial_status,
             now if initial_status=="In Progress" else "","","","Not Inspected",notes,
             st.session_state.get("username","system"),now))
            execute("UPDATE rooms SET housekeeping=? WHERE room_no=?", ("Cleaning" if initial_status=="In Progress" else "Dirty", selected_room))
            st.success(f"Task {task_id} assigned for Room {selected_room}.")
            st.rerun()

        st.markdown("#### Today's Assignment Register")
        today_register = query("SELECT * FROM housekeeping_tasks WHERE task_date=? ORDER BY priority DESC, created_at", (today_str,))
        st.dataframe(today_register, use_container_width=True, hide_index=True, height=360)

    with task_tab:
        st.markdown("#### Execute Assigned Task")
        active = query("SELECT * FROM housekeeping_tasks WHERE status IN ('Assigned','In Progress') ORDER BY task_date, priority DESC")
        if active.empty:
            st.success("No active housekeeping tasks.")
        else:
            task_id = st.selectbox("Select Task", active["task_id"].tolist(), key="hk_execute_task")
            task = active[active["task_id"] == task_id].iloc[0]
            st.info(f"Room {task['room_no']} • {task['task_type']} • {task['priority']} • Assigned to {task['assigned_to']}")
            c1,c2 = st.columns(2)
            with c1:
                linen = st.checkbox("Linen changed", value=True)
                bathroom = st.checkbox("Bathroom cleaned", value=True)
                amenities = st.checkbox("Amenities replenished", value=True)
                minibar = st.checkbox("Minibar checked", value=True)
            with c2:
                floor = st.checkbox("Floor and surfaces cleaned", value=True)
                maintenance_issue = st.checkbox("Maintenance issue identified")
                lost_item = st.checkbox("Lost-and-found item identified")
                completion_notes = st.text_area("Completion Notes")
            c1,c2 = st.columns(2)
            if c1.button("Start Task", type="secondary", use_container_width=True):
                now = datetime.now().isoformat(timespec="seconds")
                execute("UPDATE housekeeping_tasks SET status='In Progress',start_time=? WHERE task_id=?", (now,task_id))
                execute("UPDATE rooms SET housekeeping='Cleaning' WHERE room_no=?", (task["room_no"],))
                st.success("Task started."); st.rerun()
            if c2.button("Complete & Send for Inspection", type="primary", use_container_width=True):
                checklist_id = next_code("HKC", "housekeeping_checklists", "checklist_id")
                now = datetime.now().isoformat(timespec="seconds")
                execute("""INSERT INTO housekeeping_checklists VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (checklist_id,task_id,task["room_no"],int(linen),int(bathroom),int(amenities),int(minibar),int(floor),int(maintenance_issue),int(lost_item),completion_notes,st.session_state.get("username","system"),now))
                execute("UPDATE housekeeping_tasks SET status='Pending Inspection',completed_time=? WHERE task_id=?", (now,task_id))
                execute("UPDATE rooms SET housekeeping='Inspected' WHERE room_no=?", (task["room_no"],))
                if maintenance_issue:
                    ticket_id = next_code("MNT", "maintenance", "ticket_id")
                    execute("INSERT INTO maintenance VALUES(?,?,?,?,?,?,?)", (ticket_id,task["room_no"],completion_notes or "Housekeeping reported maintenance issue","High","Maintenance Team","Open",now))
                st.success("Task completed and sent for inspection."); st.rerun()

    with inspect_tab:
        st.markdown("#### Supervisor Inspection")
        pending_inspection = query("SELECT * FROM housekeeping_tasks WHERE status='Pending Inspection' ORDER BY completed_time")
        if pending_inspection.empty:
            st.success("No rooms are waiting for inspection.")
        else:
            inspect_task = st.selectbox("Task for Inspection", pending_inspection["task_id"].tolist(), key="hk_inspection_task")
            record = pending_inspection[pending_inspection["task_id"] == inspect_task].iloc[0]
            checklist = query("SELECT * FROM housekeeping_checklists WHERE task_id=? ORDER BY completed_at DESC LIMIT 1", (inspect_task,))
            st.markdown(f"**Room {record['room_no']} — {record['task_type']}**")
            if not checklist.empty:
                st.dataframe(checklist, use_container_width=True, hide_index=True)
            c1,c2 = st.columns(2)
            inspector = c1.text_input("Inspector", value=st.session_state.get("full_name", st.session_state.get("username","Supervisor")))
            inspection_result = c2.selectbox("Inspection Result", ["Passed", "Rework Required", "Out of Service"])
            inspection_notes = st.text_area("Inspection Notes")
            if st.button("Submit Inspection", type="primary"):
                now = datetime.now().isoformat(timespec="seconds")
                if inspection_result == "Passed":
                    execute("UPDATE housekeeping_tasks SET status='Completed',inspected_by=?,inspection_status='Passed',notes=COALESCE(notes,'') || ? WHERE task_id=?", (inspector," | Inspection: "+inspection_notes,inspect_task))
                    execute("UPDATE rooms SET housekeeping='Clean' WHERE room_no=?", (record["room_no"],))
                    occupied = scalar("SELECT COUNT(*) FROM reservations WHERE room_no=? AND status='Checked-in'", (record["room_no"],))
                    if not occupied:
                        execute("UPDATE rooms SET status='Available' WHERE room_no=?", (record["room_no"],))
                elif inspection_result == "Rework Required":
                    execute("UPDATE housekeeping_tasks SET status='Assigned',inspected_by=?,inspection_status='Failed',notes=COALESCE(notes,'') || ? WHERE task_id=?", (inspector," | Rework: "+inspection_notes,inspect_task))
                    execute("UPDATE rooms SET housekeeping='Dirty' WHERE room_no=?", (record["room_no"],))
                else:
                    execute("UPDATE housekeeping_tasks SET status='Completed',inspected_by=?,inspection_status='Out of Service',notes=COALESCE(notes,'') || ? WHERE task_id=?", (inspector," | OOS: "+inspection_notes,inspect_task))
                    execute("UPDATE rooms SET housekeeping='Out of Service',status='Out of Service' WHERE room_no=?", (record["room_no"],))
                st.success("Inspection recorded."); st.rerun()

    with lost_tab:
        st.markdown("#### Lost & Found Register")
        with st.form("lost_found_form", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            found_date = c1.date_input("Found Date", date.today(), key="lf_date")
            lf_room = c2.selectbox("Room / Area", rooms["room_no"].tolist()+["Lobby","Restaurant","Public Area"] if not rooms.empty else ["Lobby"])
            found_by = c3.text_input("Found By")
            item_description = st.text_input("Item Description")
            c1,c2 = st.columns(2)
            storage = c1.text_input("Storage Location", value="Security Locker")
            guest_name = c2.text_input("Guest Name, if known")
            lf_notes = st.text_area("Notes")
            save_lf = st.form_submit_button("Register Item", type="primary")
        if save_lf:
            record_id = next_code("LNF", "lost_and_found", "record_id")
            execute("INSERT INTO lost_and_found VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (record_id,str(found_date),lf_room,item_description,found_by,storage,guest_name,"Stored","","",lf_notes))
            st.success(f"Lost-and-found record {record_id} created."); st.rerun()

        lf = query("SELECT * FROM lost_and_found ORDER BY found_date DESC")
        if not lf.empty:
            st.dataframe(lf, use_container_width=True, hide_index=True, height=320)
            open_items = lf[lf["status"] == "Stored"]
            if not open_items.empty:
                c1,c2,c3 = st.columns(3)
                release_id = c1.selectbox("Release Record", open_items["record_id"].tolist())
                released_to = c2.text_input("Released To")
                if c3.button("Mark Released", type="primary"):
                    execute("UPDATE lost_and_found SET status='Released',released_to=?,released_at=? WHERE record_id=?", (released_to,datetime.now().isoformat(timespec="seconds"),release_id))
                    st.success("Item released and audit trail updated."); st.rerun()

    with analytics_tab:
        st.markdown("#### Housekeeping Performance")
        c1,c2 = st.columns(2)
        perf_from = c1.date_input("From Date", date.today()-timedelta(days=30), key="hk_perf_from")
        perf_to = c2.date_input("To Date", date.today(), key="hk_perf_to")
        perf = date_range_filter(query("SELECT * FROM housekeeping_tasks"), "task_date", perf_from, perf_to)
        if perf.empty:
            st.info("No housekeeping tasks in the selected period.")
        else:
            perf["start_dt"] = pd.to_datetime(perf["start_time"], errors="coerce")
            perf["completed_dt"] = pd.to_datetime(perf["completed_time"], errors="coerce")
            perf["turnaround_minutes"] = (perf["completed_dt"]-perf["start_dt"]).dt.total_seconds()/60
            avg_turnaround = float(perf["turnaround_minutes"].dropna().mean()) if perf["turnaround_minutes"].notna().any() else 0.0
            completed = int((perf["status"] == "Completed").sum())
            failed = int((perf["inspection_status"] == "Failed").sum())
            completion_rate = completed / len(perf) * 100 if len(perf) else 0
            a,b,c,d = st.columns(4)
            a.metric("Tasks", len(perf)); b.metric("Completed", completed); c.metric("Avg Turnaround", f"{avg_turnaround:.1f} min"); d.metric("Completion Rate", f"{completion_rate:.1f}%")
            left,right = st.columns(2)
            by_staff = perf.groupby("assigned_to", as_index=False).agg(Tasks=("task_id","count"),Completed=("status",lambda s:(s=="Completed").sum()),Avg_Minutes=("turnaround_minutes","mean"))
            left.markdown("##### Staff Performance")
            left.dataframe(by_staff, use_container_width=True, hide_index=True)
            by_type = perf.groupby("task_type").size().rename("Tasks")
            right.markdown("##### Task Mix")
            right.bar_chart(by_type)
            st.markdown("##### Inspection Exceptions")
            exceptions = perf[perf["inspection_status"].isin(["Failed","Out of Service"])]
            st.dataframe(exceptions, use_container_width=True, hide_index=True)
            st.download_button("Export Housekeeping Performance", data=excel_file({"Tasks":perf,"Staff Performance":by_staff,"Inspection Exceptions":exceptions}), file_name=f"Housekeeping_Performance_{perf_from}_{perf_to}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- Inventory ----------------
elif page == "Inventory":
    st.title("Inventory Control Tower")
    st.markdown("<div class='demo-banner'>Enterprise stock visibility • Approval-controlled adjustments • Loss-prevention audit trail</div>", unsafe_allow_html=True)
    st.caption("All manual and Excel stock adjustments require independent approval before inventory is updated.")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Inventory List", "Add New Item", "Submit Adjustment",
        "Approval Inbox", "Pending Approval", "My Submitted Requests",
        "Approval History", "LP Audit Dashboard"
    ])

    with tab1:
        stocks = stock_df()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Stock Value", money(stocks["stock_value"].sum()))
        c2.metric("Items to Reorder", int((stocks["stock_status"]=="REORDER").sum()))
        c3.metric("Inventory Items", len(stocks))
        c4.metric("Pending Batches", int(scalar(
            "SELECT COUNT(*) FROM stock_adjustment_batches WHERE status='Pending Approval'"
        )))
        c1,c2,c3 = st.columns([1.2,1,1])
        category_filter = c1.multiselect(
            "Category",
            sorted(stocks["category"].dropna().unique().tolist()),
            default=sorted(stocks["category"].dropna().unique().tolist())
        )
        status_filter = c2.multiselect(
            "Stock Status",
            sorted(stocks["stock_status"].dropna().unique().tolist()),
            default=sorted(stocks["stock_status"].dropna().unique().tolist())
        )
        item_search = c3.text_input("Search Item / Code")

        filtered_stocks = stocks.copy()
        if category_filter:
            filtered_stocks = filtered_stocks[filtered_stocks["category"].isin(category_filter)]
        if status_filter:
            filtered_stocks = filtered_stocks[filtered_stocks["stock_status"].isin(status_filter)]
        if item_search.strip():
            needle = item_search.strip().lower()
            filtered_stocks = filtered_stocks[
                filtered_stocks["item_name"].fillna("").str.lower().str.contains(needle, regex=False) |
                filtered_stocks["item_code"].fillna("").str.lower().str.contains(needle, regex=False)
            ]

        if not stocks.empty:
            chart_df = stocks.groupby("category", as_index=False)["stock_value"].sum().sort_values("stock_value", ascending=False)
            st.markdown("### Stock Value by Category")
            st.bar_chart(chart_df.set_index("category"))

        st.markdown("### Inventory Register")
        st.dataframe(filtered_stocks, use_container_width=True, hide_index=True, height=430)
        st.download_button(
            "Export Filtered Inventory",
            data=excel_file({"Inventory": filtered_stocks}),
            file_name=f"Inventory_Register_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

    with tab2:
        st.subheader("Add Inventory Item")
        with st.form("add_inventory_item", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            item_name = c1.text_input("Item Name")
            category = c2.selectbox("Category", [
                "Food","Beverage","Housekeeping","Maintenance","Linen","Cleaning","Other"
            ])
            unit = c3.selectbox("Unit", [
                "kg","gram","litre","ml","bottle","piece","box","carton","pack","set","roll","dozen"
            ])
            c1,c2,c3 = st.columns(3)
            opening_qty = c1.number_input("Opening Quantity", min_value=0.0, value=0.0, step=1.0)
            reorder_level = c2.number_input("Reorder Level", min_value=0.0, value=0.0, step=1.0)
            unit_cost = c3.number_input("Unit Cost (SAR)", min_value=0.0, value=0.0, step=0.50)
            add_item = st.form_submit_button("Add Inventory Item", type="primary")
        if add_item:
            clean_name = item_name.strip()
            if not clean_name:
                st.error("Item name is required.")
            elif scalar("SELECT COUNT(*) FROM inventory WHERE LOWER(item_name)=LOWER(?)", (clean_name,)) > 0:
                st.error("This inventory item already exists.")
            else:
                item_code = next_code("INV", "inventory")
                now = datetime.now().isoformat(timespec="seconds")
                execute("INSERT INTO inventory VALUES(?,?,?,?,?,?,?,?,?)", (
                    item_code, clean_name, category, unit, 0.0, 0.0, 0.0,
                    reorder_level, unit_cost
                ))
                execute("""INSERT INTO opening_stock_requests(
                    item_code,item_name,requested_qty,requested_by,requested_username,requested_at,status
                ) VALUES(?,?,?,?,?,?,?)""", (
                    item_code, clean_name, float(opening_qty), user["full_name"],
                    user["username"], now, "Pending Approval"
                ))
                approvals.submit_request(
                    execute, scalar,
                    module="Opening Stock",
                    record_id=item_code,
                    title=f"Opening stock — {clean_name} ({opening_qty:g} {unit})",
                    submitted_by=user["full_name"],
                    submitted_username=user["username"],
                    approver_chain=["Manager"],
                    sla_hours=24
                )
                st.success(f"{clean_name} added with code {item_code}. Opening stock is pending approval.")
                st.rerun()

    with tab3:
        st.subheader("Submit Stock Adjustment for Approval")
        mode = st.radio("Entry Method", ["Excel Upload", "Manual Entry"], horizontal=True)
        location = st.selectbox("Store / Location", [
            "Main Store", "Kitchen Store", "Housekeeping Store", "Maintenance Store", "Other"
        ])
        preview = pd.DataFrame()
        source_name = "Manual Entry"

        if mode == "Excel Upload":
            template = pd.DataFrame([
                ["Chicken", "Stock Received", 25, "Supplier delivery correction"],
                ["Rice", "Stock Issued / Used", 10, "Physical count shortage"]
            ], columns=["Item", "Adjustment Type", "Quantity", "Remarks"])
            st.download_button(
                "Download Upload Template",
                data=excel_file({"Stock Adjustment": template}),
                file_name="Hotel_ERP_Stock_Adjustment_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            uploaded = st.file_uploader("Upload completed Excel file", type=["xlsx", "xls"])
            if uploaded is not None:
                source_name = uploaded.name
                try:
                    upload_df = pd.read_excel(uploaded)
                    preview = adjustment_preview(upload_df)
                except Exception as exc:
                    st.error(f"Unable to read the Excel file: {exc}")
        else:
            inventory_items = query("SELECT item_code,item_name,unit FROM inventory ORDER BY item_name")
            with st.form("manual_adjustment_approval", clear_on_submit=False):
                item = st.selectbox("Inventory Item", inventory_items["item_name"].tolist())
                adjustment_type = st.selectbox("Adjustment Type", ["Stock Received", "Stock Issued / Used"])
                quantity = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)
                reason = st.text_area("Reason / Remarks")
                build_preview = st.form_submit_button("Validate Entry")
            if build_preview:
                preview = adjustment_preview(pd.DataFrame([{
                    "Item": item, "Adjustment Type": adjustment_type,
                    "Quantity": quantity, "Remarks": reason
                }]))
                st.session_state["manual_adjustment_preview"] = preview
            elif "manual_adjustment_preview" in st.session_state:
                preview = st.session_state["manual_adjustment_preview"]

        if not preview.empty:
            st.markdown("### Validation & Variance Preview")
            def highlight_validation(row):
                if row["Validation"] == "Error":
                    return ["background-color: #ffd6d6"] * len(row)
                if abs(float(row["Difference"])) > 0:
                    return ["background-color: #fff2cc"] * len(row)
                return [""] * len(row)
            st.dataframe(preview.style.apply(highlight_validation, axis=1), use_container_width=True, hide_index=True)
            errors = int((preview["Validation"] == "Error").sum())
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Uploaded Lines", len(preview))
            c2.metric("Validation Errors", errors)
            c3.metric("Net Quantity Difference", f"{preview['Difference'].sum():,.2f}")
            c4.metric("Net Value Impact", money(preview["Variance Value"].sum()))
            approval_note = st.text_area("Submission Note", key="adjustment_submission_note")
            confirm = st.checkbox("I confirm the quantities and reasons are correct and submit them for approval.")
            if st.button("Submit Batch for Approval", type="primary", disabled=(errors > 0 or not confirm)):
                batch_no = next_adjustment_batch()
                now = datetime.now().isoformat(timespec="seconds")
                increase_qty = float(preview.loc[preview["Difference"] > 0, "Difference"].sum())
                decrease_qty = abs(float(preview.loc[preview["Difference"] < 0, "Difference"].sum()))
                execute("""INSERT INTO stock_adjustment_batches(
                    batch_no,batch_date,adjustment_source,file_name,location,total_lines,
                    total_increase_qty,total_decrease_qty,total_variance_value,
                    submitted_by,submitted_username,submitted_at,status,review_comments
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    batch_no, str(date.today()), mode, source_name, location, len(preview),
                    increase_qty, decrease_qty, float(preview["Variance Value"].sum()),
                    user["full_name"], user["username"], now, "Pending Approval", approval_note.strip()
                ))
                with conn() as c:
                    c.executemany("""INSERT INTO stock_adjustment_lines(
                        batch_no,item_code,item_name,adjustment_type,quantity,reason,
                        system_qty,projected_qty,difference_qty,unit_cost,variance_value,
                        validation_status,validation_message
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", [(
                        batch_no, r["Item Code"], r["Item"], r["Adjustment Type"], float(r["Quantity"]),
                        r["Remarks"], float(r["System Quantity"]), float(r["Projected Quantity"]),
                        float(r["Difference"]), float(r["Unit Cost"]), float(r["Variance Value"]),
                        r["Validation"], r["Message"]
                    ) for _, r in preview.iterrows()])
                    c.commit()
                variance_value = float(preview["Variance Value"].abs().sum())
                chain = approvals.approval_chain_for_value(variance_value)
                approvals.submit_request(
                    execute, scalar,
                    module="Stock Adjustment",
                    record_id=batch_no,
                    title=f"Stock adjustment — {location} ({len(preview)} line(s), {money(variance_value)})",
                    submitted_by=user["full_name"],
                    submitted_username=user["username"],
                    approver_chain=chain,
                    sla_hours=24
                )
                st.session_state.pop("manual_adjustment_preview", None)
                st.success(f"Batch {batch_no} submitted. Inventory has not been updated.")
                st.rerun()

    with tab4:
        st.subheader("Approval Inbox")
        st.caption("Requests waiting on your role. You cannot approve your own submissions. Higher-value requests may require multiple sequential sign-offs.")
        inbox_raw = approvals.get_inbox(query, user["username"], user["role"])
        inbox = inbox_raw[inbox_raw["module"]!="Purchase Order"] if not inbox_raw.empty else inbox_raw
        if inbox.empty:
            st.info("Your approval inbox is empty.")
        else:
            st.dataframe(inbox, use_container_width=True, hide_index=True)
            request_id = st.selectbox("Select Request", inbox["request_id"].tolist(), key="inbox_request")
            req_row = inbox[inbox["request_id"] == request_id].iloc[0]
            module = req_row["module"]

            if module == "Stock Adjustment":
                batch_no = req_row["record_id"]
                lines = query("SELECT * FROM stock_adjustment_lines WHERE batch_no=? ORDER BY line_id", (batch_no,))
                st.dataframe(lines[[
                    "item_code","item_name","adjustment_type","quantity","system_qty",
                    "projected_qty","difference_qty","unit_cost","variance_value","reason"
                ]], use_container_width=True, hide_index=True)

                decision = st.radio("Decision", ["Approve", "Reject", "Return"], horizontal=True, key="inbox_decision")
                comments = st.text_area("Comments", key="inbox_comments")

                if st.button("Submit Decision", type="primary", key="inbox_submit"):
                    if not approvals.is_step_pending(query, int(req_row["step_id"])):
                        st.error("This request was already processed by another approver. Refresh the inbox.")
                        st.rerun()
                    elif decision != "Approve" and not comments.strip():
                        st.error("Comments are required for rejection or return.")
                    else:
                        posting_error = None
                        result = None
                        try:
                            with conn() as c:
                                if decision == "Approve":
                                    for _, line in lines.iterrows():
                                        inv = c.execute("""SELECT opening_qty+received_qty-issued_qty
                                                           FROM inventory WHERE item_code=?""", (line["item_code"],)).fetchone()
                                        if not inv:
                                            raise RuntimeError(f"Item {line['item_code']} no longer exists.")
                                        current_qty = float(inv[0] or 0)
                                        qty = float(line["quantity"] or 0)
                                        if line["adjustment_type"] == "Stock Issued / Used" and qty > current_qty + 0.000001:
                                            raise RuntimeError(f"Insufficient current stock for {line['item_name']}. Available {current_qty:.2f}.")

                                result = approvals.act_on_step_conn(c, request_id, int(req_row["step_id"]), decision,
                                                                     comments, user["full_name"], user["username"])

                                if result == "final_approved":
                                    for _, line in lines.iterrows():
                                        before = float(c.execute("""SELECT opening_qty+received_qty-issued_qty
                                                                   FROM inventory WHERE item_code=?""", (line["item_code"],)).fetchone()[0] or 0)
                                        qty = float(line["quantity"] or 0)
                                        if line["adjustment_type"] == "Stock Received":
                                            c.execute("UPDATE inventory SET received_qty=received_qty+? WHERE item_code=?", (qty, line["item_code"]))
                                            change = qty
                                        else:
                                            c.execute("UPDATE inventory SET issued_qty=issued_qty+? WHERE item_code=?", (qty, line["item_code"]))
                                            change = -qty
                                        after = before + change
                                        c.execute("""INSERT INTO inventory_audit_log(
                                            batch_no,item_code,item_name,transaction_type,before_qty,change_qty,
                                            after_qty,unit_cost,value_impact,reason,action_by,action_username,
                                            action_at,approval_by,approval_at
                                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                                            batch_no, line["item_code"], line["item_name"], line["adjustment_type"],
                                            before, change, after, float(line["unit_cost"] or 0),
                                            change * float(line["unit_cost"] or 0), line["reason"],
                                            req_row["submitted_by"], "", req_row["submitted_at"],
                                            user["full_name"], datetime.now().isoformat(timespec="seconds")
                                        ))
                                    c.execute("UPDATE stock_adjustment_batches SET status='Posted' WHERE batch_no=?", (batch_no,))
                                elif result in ("rejected", "returned"):
                                    new_status = "Rejected" if result == "rejected" else "Returned for Correction"
                                    c.execute("UPDATE stock_adjustment_batches SET status=? WHERE batch_no=?", (new_status, batch_no))
                                c.commit()
                        except Exception as e:
                            posting_error = str(e)

                        if posting_error:
                            st.error(posting_error)
                        elif result == "final_approved":
                            st.success(f"{batch_no} approved and posted to inventory.")
                            st.rerun()
                        elif result == "next_level":
                            st.success(f"{batch_no} approved at this level — advanced to the next approver.")
                            st.rerun()
                        elif result == "rejected":
                            st.success(f"{batch_no} marked as Rejected.")
                            st.rerun()
                        elif result == "returned":
                            st.success(f"{batch_no} marked as Returned for Correction.")
                            st.rerun()

            elif module == "GRN Receiving":
                grn_no = req_row["record_id"]
                grn_rows = query("SELECT * FROM goods_receipts WHERE grn_no=?", (grn_no,))
                if grn_rows.empty:
                    st.error("This GRN record could not be found.")
                else:
                    grn = grn_rows.iloc[0]
                    st.dataframe(grn_rows[[
                        "grn_no","grn_date","po_no","supplier_name","item_name",
                        "ordered_qty","received_qty","rejected_qty","accepted_qty","warehouse","remarks"
                    ]], use_container_width=True, hide_index=True)

                    decision = st.radio("Decision", ["Approve", "Reject"], horizontal=True, key="grn_decision")
                    comments = st.text_area("Comments", key="grn_comments")

                    if st.button("Submit Decision", type="primary", key="grn_submit"):
                        if not approvals.is_step_pending(query, int(req_row["step_id"])):
                            st.error("This request was already processed by another approver. Refresh the inbox.")
                            st.rerun()
                        elif decision == "Reject" and not comments.strip():
                            st.error("Comments are required for rejection.")
                        else:
                            now = datetime.now().isoformat(timespec="seconds")
                            grn_error = None
                            result = None
                            try:
                                with conn() as c:
                                    result = approvals.act_on_step_conn(c, request_id, int(req_row["step_id"]), decision,
                                                                         comments, user["full_name"], user["username"])
                                    if result == "final_approved":
                                        po_row = query("SELECT * FROM purchase_orders WHERE po_no=?", (grn["po_no"],)).iloc[0]
                                        accepted = float(grn["accepted_qty"] or 0)
                                        current_qty = float(scalar(
                                            "SELECT opening_qty+received_qty-issued_qty FROM inventory WHERE item_code=?",
                                            (grn["item_code"],), default=0
                                        ))
                                        c.execute(
                                            """UPDATE inventory SET received_qty=received_qty+?, unit_cost=?
                                               WHERE item_code=?""",
                                            (accepted, float(po_row["unit_cost"]), grn["item_code"])
                                        )
                                        c.execute(
                                            """INSERT INTO inventory_audit_log(
                                                batch_no,item_code,item_name,transaction_type,before_qty,change_qty,
                                                after_qty,unit_cost,value_impact,reason,action_by,action_username,
                                                action_at,approval_by,approval_at
                                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                            (
                                                grn_no, grn["item_code"], grn["item_name"], "GRN Receiving",
                                                current_qty, accepted, current_qty+accepted, float(po_row["unit_cost"]),
                                                accepted*float(po_row["unit_cost"]), grn["remarks"],
                                                req_row["submitted_by"], "", req_row["submitted_at"], user["full_name"], now
                                            )
                                        )
                                        c.execute("UPDATE goods_receipts SET status='Posted' WHERE grn_no=?", (grn_no,))
                                        total_posted = float(c.execute(
                                            "SELECT COALESCE(SUM(accepted_qty),0) FROM goods_receipts WHERE po_no=? AND status='Posted'",
                                            (grn["po_no"],)
                                        ).fetchone()[0])
                                        new_po_status = "Received" if total_posted >= float(po_row["qty"])-0.0001 else "Partially Received"
                                        c.execute(
                                            "UPDATE purchase_orders SET status=?, received_at=?, grn_no=? WHERE po_no=?",
                                            (new_po_status, now, grn_no, grn["po_no"])
                                        )
                                    elif result == "rejected":
                                        c.execute("UPDATE goods_receipts SET status='Rejected' WHERE grn_no=?", (grn_no,))
                                    c.commit()
                            except Exception as e:
                                grn_error = str(e)

                            if grn_error:
                                st.error(f"Approval could not be completed and was rolled back: {grn_error}")
                            elif result == "final_approved":
                                st.success(f"{grn_no} approved and posted to inventory.")
                                st.rerun()
                            elif result == "next_level":
                                st.success(f"{grn_no} approved at this level — advanced to the next approver.")
                                st.rerun()
                            elif result == "rejected":
                                st.success(f"{grn_no} rejected. No stock was posted.")
                                st.rerun()

            elif module == "Opening Stock":
                item_code = req_row["record_id"]
                req_details = query("SELECT * FROM opening_stock_requests WHERE item_code=?", (item_code,))
                if req_details.empty:
                    st.error("This opening stock request could not be found.")
                else:
                    detail = req_details.iloc[0]
                    st.dataframe(req_details[["item_code","item_name","requested_qty","requested_by","requested_at"]],
                                 use_container_width=True, hide_index=True)

                    decision = st.radio("Decision", ["Approve", "Reject"], horizontal=True, key="opening_decision")
                    comments = st.text_area("Comments", key="opening_comments")

                    if st.button("Submit Decision", type="primary", key="opening_submit"):
                        if not approvals.is_step_pending(query, int(req_row["step_id"])):
                            st.error("This request was already processed by another approver. Refresh the inbox.")
                            st.rerun()
                        elif decision == "Reject" and not comments.strip():
                            st.error("Comments are required for rejection.")
                        else:
                            now = datetime.now().isoformat(timespec="seconds")
                            opening_error = None
                            result = None
                            try:
                                with conn() as c:
                                    result = approvals.act_on_step_conn(c, request_id, int(req_row["step_id"]), decision,
                                                                         comments, user["full_name"], user["username"])
                                    if result == "final_approved":
                                        unit_cost = float(c.execute("SELECT unit_cost FROM inventory WHERE item_code=?", (item_code,)).fetchone()[0] or 0)
                                        c.execute("UPDATE inventory SET opening_qty=? WHERE item_code=?", (float(detail["requested_qty"]), item_code))
                                        c.execute(
                                            """INSERT INTO inventory_audit_log(
                                                batch_no,item_code,item_name,transaction_type,before_qty,change_qty,
                                                after_qty,unit_cost,value_impact,reason,action_by,action_username,
                                                action_at,approval_by,approval_at
                                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                            (
                                                f"OPEN-{item_code}", item_code, detail["item_name"], "Opening Stock",
                                                0, float(detail["requested_qty"]), float(detail["requested_qty"]), unit_cost,
                                                float(detail["requested_qty"])*unit_cost, "Initial opening balance",
                                                detail["requested_by"], detail["requested_username"], detail["requested_at"],
                                                user["full_name"], now
                                            )
                                        )
                                        c.execute("UPDATE opening_stock_requests SET status='Approved' WHERE item_code=?", (item_code,))
                                    elif result == "rejected":
                                        c.execute("UPDATE opening_stock_requests SET status='Rejected' WHERE item_code=?", (item_code,))
                                    c.commit()
                            except Exception as e:
                                opening_error = str(e)

                            if opening_error:
                                st.error(f"Approval could not be completed and was rolled back: {opening_error}")
                            elif result == "final_approved":
                                st.success(f"Opening stock for {detail['item_name']} approved and posted.")
                                st.rerun()
                            elif result == "next_level":
                                st.success("Opening stock request approved at this level — advanced to the next approver.")
                                st.rerun()
                            elif result == "rejected":
                                st.success(f"Opening stock request for {detail['item_name']} rejected. Item remains at zero stock.")
                                st.rerun()
            else:
                st.info("Unrecognized request module.")
    with tab5:
        st.subheader("Pending Approval — All Requests")
        st.caption("Every open request across all approvers, for managers wanting the full picture.")
        pending = approvals.get_pending(query)
        if pending.empty:
            st.info("Nothing is currently pending.")
        else:
            st.dataframe(pending, use_container_width=True, hide_index=True)

    with tab6:
        st.subheader("My Submitted Requests")
        mine = approvals.get_my_requests(query, user["username"])
        if mine.empty:
            st.info("You haven't submitted any requests yet.")
        else:
            st.dataframe(mine, use_container_width=True, hide_index=True)

    with tab7:
        st.subheader("Approval History")
        history = approvals.get_history(query)
        if history.empty:
            st.info("No approval decisions recorded yet.")
        else:
            st.dataframe(history, use_container_width=True, hide_index=True)

    with tab8:
        st.subheader("Loss Prevention / Internal Audit Dashboard")
        batches = query("SELECT * FROM stock_adjustment_batches")
        audit = query("SELECT * FROM inventory_audit_log ORDER BY action_at DESC")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Pending", int((batches["status"]=="Pending Approval").sum()) if not batches.empty else 0)
        c2.metric("Posted", int((batches["status"]=="Posted").sum()) if not batches.empty else 0)
        c3.metric("Rejected", int((batches["status"]=="Rejected").sum()) if not batches.empty else 0)
        c4.metric("Stock Loss Value", money(abs(audit.loc[audit["value_impact"]<0,"value_impact"].sum())) if not audit.empty else money(0))
        c5.metric("Stock Gain Value", money(audit.loc[audit["value_impact"]>0,"value_impact"].sum()) if not audit.empty else money(0))

        if audit.empty:
            st.info("No approved stock adjustment audit records yet.")
        else:
            st.markdown("### High-Value and Recent Adjustments")
            audit_view = audit.copy()
            audit_view["absolute_value"] = audit_view["value_impact"].abs()
            st.dataframe(audit_view.sort_values("absolute_value", ascending=False).head(50), use_container_width=True, hide_index=True)
            st.markdown("### Top Adjusted Items by Value")
            top_items = audit.groupby("item_name", as_index=False).agg(
                net_quantity=("change_qty","sum"),
                net_value=("value_impact","sum"),
                adjustment_count=("audit_id","count")
            ).sort_values("adjustment_count", ascending=False)
            st.dataframe(top_items, use_container_width=True, hide_index=True)
            st.markdown("### User Activity")
            users_activity = audit.groupby(["action_by","approval_by"], as_index=False).agg(
                batches=("batch_no","nunique"),
                lines=("audit_id","count"),
                value_impact=("value_impact","sum")
            )
            st.dataframe(users_activity, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Complete LP Audit Trail",
                data=excel_file({"Batches": batches, "Audit Log": audit, "Top Items": top_items}),
                file_name="Hotel_ERP_LP_Inventory_Audit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

# ---------------- Purchasing ----------------
elif page == "Purchasing":
    st.title("Procurement Control Tower")
    st.markdown("<div class='demo-banner'>Supplier management • Multi-level approvals • GRN • Three-way matching • Vendor payments</div>", unsafe_allow_html=True)

    po_all = query("SELECT * FROM purchase_orders")
    grn_all = query("SELECT * FROM goods_receipts")
    inv_all = query("SELECT * FROM supplier_invoices")
    pending_po_value = float(po_all.loc[po_all["status"].astype(str).str.contains("Pending", case=False, na=False), "total"].sum()) if not po_all.empty else 0.0
    open_invoice_value = float((inv_all["total_amount"].fillna(0) - inv_all["paid_amount"].fillna(0)).clip(lower=0).sum()) if not inv_all.empty else 0.0
    overdue_count = 0
    if not inv_all.empty:
        due_dates = pd.to_datetime(inv_all["due_date"], errors="coerce")
        overdue_count = int(((due_dates < pd.Timestamp(date.today())) & (inv_all["payment_status"].fillna("") != "Paid")).sum())

    p1,p2,p3,p4,p5 = st.columns(5)
    p1.metric("Total PO Value", money(po_all["total"].sum()) if not po_all.empty else money(0))
    p2.metric("Pending Approval", money(pending_po_value))
    p3.metric("GRNs", len(grn_all))
    p4.metric("Open Payables", money(open_invoice_value))
    p5.metric("Overdue Invoices", overdue_count)

    def required_approval(total_value):
        if total_value <= 5000:
            return "Manager"
        elif total_value <= 20000:
            return "Accounts"
        return "Admin"

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Suppliers",
        "Create Purchase Order",
        "Approval Queue",
        "Goods Receipt (GRN)",
        "Invoice Booking",
        "Invoice Payments",
        "Cancel PO",
        "Analytics & 3-Way Match"
    ])

    with tab1:
        st.subheader("Supplier Master")
        with st.form("supplier"):
            c1,c2,c3=st.columns(3)
            name=c1.text_input("Supplier Name")
            vat=c2.text_input("VAT Number")
            mobile=c3.text_input("Mobile")
            c1,c2=st.columns(2)
            email=c1.text_input("Email")
            terms=c2.number_input("Default Payment Terms (Days)",0,180,30)
            save=st.form_submit_button("Add Supplier",type="primary")

        if save:
            if not name.strip():
                st.error("Supplier name is required.")
            elif scalar("SELECT COUNT(*) FROM suppliers WHERE LOWER(supplier_name)=LOWER(?)",(name.strip(),)) > 0:
                st.error("Supplier already exists.")
            else:
                sid=next_code("SUP","suppliers")
                execute("INSERT INTO suppliers VALUES(?,?,?,?,?,?)",(sid,name.strip(),vat,mobile,email,terms))
                st.success(f"Supplier {name.strip()} added.")
                st.rerun()

        st.dataframe(query("SELECT * FROM suppliers ORDER BY supplier_name"),use_container_width=True,hide_index=True)

    with tab2:
        st.subheader("Create Purchase Order")
        suppliers=query("SELECT * FROM suppliers ORDER BY supplier_name")
        inv=query("SELECT * FROM inventory ORDER BY item_name")

        if suppliers.empty:
            st.info("Create a supplier first.")
        else:
            supplier_name=st.selectbox("Supplier",suppliers["supplier_name"].tolist())
            supplier_row=suppliers[suppliers["supplier_name"]==supplier_name].iloc[0]

            with st.form("po_create"):
                c1,c2,c3=st.columns(3)
                item=c1.selectbox("Item",inv["item_name"].tolist())
                qty=c2.number_input("Quantity",min_value=0.01,value=10.0)
                item_row=inv[inv["item_name"]==item].iloc[0]
                unit_cost=c3.number_input("Unit Cost",min_value=0.0,value=float(item_row["unit_cost"]))

                c1,c2,c3=st.columns(3)
                vat_rate=c1.number_input("VAT %",0.0,100.0,15.0)
                payment_method=c2.selectbox("Payment Method",["Bank Transfer","Credit","Cash","Cheque","Card"])
                payment_terms=c3.number_input("Payment Terms (Days)",0,365,int(supplier_row["payment_terms"]))

                subtotal=qty*unit_cost
                vat_amount=subtotal*vat_rate/100
                total=subtotal+vat_amount
                chain = approvals.approval_chain_for_value(total)
                approval_level_display = " → ".join(chain)
                st.info(
                    f"Subtotal: {money(subtotal)} | VAT: {money(vat_amount)} | "
                    f"Total: {money(total)} | Approval chain: {approval_level_display}"
                )
                submit=st.form_submit_button("Create & Submit PO",type="primary")

            if submit:
                po=next_code("PO","purchase_orders")
                execute(
                    """INSERT INTO purchase_orders(
                        po_no,po_date,supplier_id,supplier_name,item_code,item_name,
                        qty,unit_cost,vat_rate,total,status,payment_method,
                        payment_terms_days,requested_by,requested_username,approval_level,approved_by,
                        approved_at,rejection_reason,payment_status,paid_amount,
                        received_at,grn_no,invoice_status
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        po,str(date.today()),supplier_row["supplier_id"],supplier_name,
                        item_row["item_code"],item,qty,unit_cost,vat_rate,total,
                        "Pending Approval",payment_method,payment_terms,user["full_name"],user["username"],
                        approval_level_display,"","","","Unpaid",0.0,"","","Not Booked"
                    )
                )
                approvals.submit_request(
                    execute, scalar,
                    module="Purchase Order",
                    record_id=po,
                    title=f"Purchase Order {po} — {item} ({money(total)})",
                    submitted_by=user["full_name"],
                    submitted_username=user["username"],
                    approver_chain=chain,
                    sla_hours=24
                )
                st.success(f"{po} submitted for approval ({approval_level_display}).")
                st.rerun()

        st.dataframe(
            query("""SELECT po_no,po_date,supplier_name,item_name,qty,total,status,
                            approval_level,grn_no,invoice_status,payment_status
                     FROM purchase_orders ORDER BY po_no DESC"""),
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.subheader("Approval Queue")
        st.caption(
            "You cannot approve a purchase order you created yourself. Higher-value POs require "
            "sequential approval through Manager, then Accounts, then Admin."
        )

        full_status = query("SELECT status FROM purchase_orders")
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Pending Approval", int((full_status["status"]=="Pending Approval").sum()) if not full_status.empty else 0)
        c2.metric("Approved", int((full_status["status"]=="Approved").sum()) if not full_status.empty else 0)
        c3.metric("Received", int((full_status["status"]=="Received").sum()) if not full_status.empty else 0)
        c4.metric("Rejected", int((full_status["status"]=="Rejected").sum()) if not full_status.empty else 0)

        queue_display=query("""
            SELECT po_no,po_date,supplier_name,item_name,qty,total,status,
                   approval_level,requested_by,approved_by,grn_no,invoice_status
            FROM purchase_orders
            WHERE status IN ('Pending Approval','Approved','Rejected','Partially Received','Received','Cancelled')
            ORDER BY po_no DESC
        """)
        if queue_display.empty:
            st.info("No purchase orders available.")
        else:
            st.dataframe(queue_display, use_container_width=True, hide_index=True)

        inbox_raw = approvals.get_inbox(query, user["username"], user["role"])
        inbox = inbox_raw[inbox_raw["module"]=="Purchase Order"] if not inbox_raw.empty else inbox_raw

        if inbox.empty:
            st.info("No purchase orders are awaiting your approval level (or your own submissions are excluded).")
        else:
            st.dataframe(inbox, use_container_width=True, hide_index=True)
            selected_request=st.selectbox("Select Request", inbox["request_id"].tolist(), key="po_inbox_request")
            req_row=inbox[inbox["request_id"]==selected_request].iloc[0]
            selected_po=req_row["record_id"]

            decision=st.radio("Decision",["Approve","Reject"],horizontal=True,key="po_decision")
            rejection_reason=st.text_area("Rejection Reason",disabled=(decision=="Approve"),key="po_rejection_reason")

            if st.button("Submit Decision",type="primary",key="po_submit_decision"):
                if not approvals.is_step_pending(query, int(req_row["step_id"])):
                    st.error("This request was already processed by another approver. Refresh the queue.")
                    st.rerun()
                elif decision=="Reject" and not rejection_reason.strip():
                    st.error("Rejection reason is required.")
                else:
                    now=datetime.now().isoformat(timespec="seconds")
                    po_error=None
                    result=None
                    with st.spinner("Recording decision..."):
                        try:
                            with conn() as c:
                                result = approvals.act_on_step_conn(
                                    c, selected_request, int(req_row["step_id"]), decision,
                                    rejection_reason.strip() if decision=="Reject" else "",
                                    user["full_name"], user["username"]
                                )
                                if result=="rejected":
                                    c.execute(
                                        """UPDATE purchase_orders
                                           SET status='Rejected',approved_by=?,approved_at=?,rejection_reason=?
                                           WHERE po_no=?""",
                                        (user["full_name"],now,rejection_reason.strip(),selected_po)
                                    )
                                elif result=="final_approved":
                                    c.execute(
                                        """UPDATE purchase_orders
                                           SET status='Approved',approved_by=?,approved_at=?,rejection_reason=''
                                           WHERE po_no=?""",
                                        (user["full_name"],now,selected_po)
                                    )
                                elif result=="next_level":
                                    c.execute(
                                        """UPDATE purchase_orders
                                           SET approved_by=?,approved_at=?
                                           WHERE po_no=?""",
                                        (user["full_name"],now,selected_po)
                                    )
                                affected = 1
                                c.commit()
                        except Exception as e:
                            po_error=str(e)

                    if po_error:
                        st.error(po_error)
                    elif result=="rejected":
                        st.success(f"{selected_po} rejected.")
                        st.rerun()
                    elif result=="final_approved":
                        st.success(f"{selected_po} fully approved.")
                        st.rerun()
                    elif result=="next_level":
                        st.success(f"{selected_po} approved at this level — advanced to the next approver.")
                        st.rerun()

    with tab4:
        st.subheader("Goods Receipt Note (GRN / GRR)")
        approved=query("""
            SELECT po.*,
                   COALESCE((SELECT SUM(accepted_qty) FROM goods_receipts gr
                             WHERE gr.po_no=po.po_no AND gr.status='Posted'),0) AS already_received,
                   COALESCE((SELECT SUM(accepted_qty) FROM goods_receipts gr
                             WHERE gr.po_no=po.po_no AND gr.status='Pending Approval'),0) AS pending_received
            FROM purchase_orders po
            WHERE po.status IN ('Approved','Partially Received')
            ORDER BY po.po_no
        """)

        if approved.empty:
            st.info("No approved purchase orders are pending receipt.")
        else:
            po_no=st.selectbox("Approved PO",approved["po_no"].tolist())
            row=approved[approved["po_no"]==po_no].iloc[0]
            outstanding=float(row["qty"])-float(row["already_received"])-float(row["pending_received"])

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Ordered Qty",f"{float(row['qty']):,.2f}")
            c2.metric("Already Received",f"{float(row['already_received']):,.2f}")
            c3.metric("Outstanding Qty",f"{outstanding:,.2f}")
            c4.metric("PO Value",money(row["total"]))

            with st.form("grn_form"):
                c1,c2,c3=st.columns(3)
                received_qty=c1.number_input("Received Quantity",min_value=0.0,max_value=float(outstanding),value=float(outstanding))
                rejected_qty=c2.number_input("Rejected Quantity",min_value=0.0,max_value=float(received_qty),value=0.0)
                warehouse=c3.selectbox("Warehouse",["Main Store","Kitchen Store","Housekeeping Store","Maintenance Store"])
                remarks=st.text_area("GRN Remarks")
                create_grn=st.form_submit_button("Create GRN & Submit for Approval",type="primary")

            if create_grn:
                accepted_qty=float(received_qty)-float(rejected_qty)
                if received_qty <= 0:
                    st.error("Received quantity must be greater than zero.")
                elif accepted_qty < 0:
                    st.error("Rejected quantity cannot exceed received quantity.")
                else:
                    grn_no=next_code("GRN","goods_receipts")
                    execute(
                        """INSERT INTO goods_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            grn_no,str(date.today()),po_no,row["supplier_name"],row["item_code"],
                            row["item_name"],float(row["qty"]),float(received_qty),
                            float(rejected_qty),accepted_qty,warehouse,user["full_name"],
                            remarks,"Pending Approval"
                        )
                    )
                    grn_value = accepted_qty * float(row["unit_cost"])
                    chain = approvals.approval_chain_for_value(grn_value)
                    approvals.submit_request(
                        execute, scalar,
                        module="GRN Receiving",
                        record_id=grn_no,
                        title=f"Goods receipt {grn_no} — {row['item_name']} ({accepted_qty:.2f}, {money(grn_value)})",
                        submitted_by=user["full_name"],
                        submitted_username=user["username"],
                        approver_chain=chain,
                        sla_hours=24
                    )
                    st.success(
                        f"{grn_no} submitted for approval ({' → '.join(chain)}). Stock has not been "
                        f"added to inventory yet — it will update once fully approved."
                    )
                    st.rerun()

        st.markdown("### GRN Register")
        st.dataframe(
            query("""SELECT grn_no,grn_date,po_no,supplier_name,item_name,
                            ordered_qty,received_qty,rejected_qty,accepted_qty,
                            warehouse,received_by,status
                     FROM goods_receipts ORDER BY grn_no DESC"""),
            use_container_width=True,
            hide_index=True
        )

    with tab5:
        st.subheader("Supplier Invoice Booking")
        received_pos=query("""
            SELECT
                po.po_no,
                po.po_date,
                po.supplier_id,
                po.supplier_name,
                po.item_code,
                po.item_name,
                po.qty,
                po.unit_cost,
                po.vat_rate,
                po.total,
                po.status,
                po.payment_method,
                po.payment_terms_days,
                po.requested_by,
                po.approval_level,
                po.approved_by,
                po.approved_at,
                po.rejection_reason,
                po.payment_status,
                po.paid_amount,
                po.received_at,
                po.invoice_status,
                gr.grn_no AS receipt_grn_no,
                gr.accepted_qty
            FROM purchase_orders po
            JOIN goods_receipts gr ON gr.po_no=po.po_no
            WHERE po.status IN ('Received','Partially Received')
              AND NOT EXISTS (
                  SELECT 1 FROM supplier_invoices si WHERE si.grn_no = gr.grn_no
              )
            ORDER BY po.po_no
        """)

        if received_pos.empty:
            st.info("No GRN-posted purchase orders are awaiting invoice booking.")
        else:
            received_pos["po_grn_label"]=received_pos.apply(
                lambda r: f"{r['po_no']} | {r['receipt_grn_no']} | {r['supplier_name']} | {money(r['total'])}",
                axis=1
            )
            selected_label=st.selectbox("PO / GRN",received_pos["po_grn_label"].tolist())
            # Matched on the FULL label, not just po_no — a PO can have multiple
            # GRNs (partial receipts), and matching on po_no alone would always
            # resolve to the first GRN row regardless of which one was picked.
            row=received_pos[received_pos["po_grn_label"]==selected_label].iloc[0]
            po_no=row["po_no"]

            # Only GRNs not already invoiced appear above, so each GRN can now
            # be booked exactly once regardless of how many other GRNs exist
            # for the same PO.
            po_qty=float(row["accepted_qty"] or 0)
            po_unit_cost=float(row["unit_cost"] or 0)
            po_vat_rate=float(row["vat_rate"] or 0)

            subtotal=po_qty*po_unit_cost
            vat_amount=subtotal*po_vat_rate/100
            total_amount=subtotal+vat_amount

            with st.form("invoice_booking"):
                c1,c2,c3=st.columns(3)
                supplier_invoice_no=c1.text_input("Supplier Invoice Number")
                invoice_date=c2.date_input("Invoice Date",date.today())
                due_date=c3.date_input(
                    "Due Date",
                    date.today()+timedelta(days=int(row["payment_terms_days"]))
                )
                c1,c2,c3=st.columns(3)
                c1.metric("Subtotal",money(subtotal))
                c2.metric("VAT",money(vat_amount))
                c3.metric("Invoice Total",money(total_amount))
                book_invoice=st.form_submit_button("Book Supplier Invoice",type="primary")

            if book_invoice:
                if not supplier_invoice_no.strip():
                    st.error("Supplier invoice number is required.")
                elif scalar(
                    "SELECT COUNT(*) FROM supplier_invoices WHERE invoice_no=? AND supplier_name=?",
                    (supplier_invoice_no.strip(),str(row["supplier_name"]))
                ) > 0:
                    st.error("This supplier invoice is already booked.")
                else:
                    invoice_id=next_code("INVBOOK","supplier_invoices")
                    execute(
                        """INSERT INTO supplier_invoices(
                            invoice_id,invoice_no,invoice_date,po_no,grn_no,supplier_name,
                            subtotal,vat_amount,total_amount,due_date,booked_by,booked_at,status
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            invoice_id,supplier_invoice_no.strip(),str(invoice_date),
                            po_no,str(row["receipt_grn_no"]),str(row["supplier_name"]),subtotal,
                            vat_amount,total_amount,str(due_date),user["full_name"],
                            datetime.now().isoformat(timespec="seconds"),"Booked"
                        )
                    )
                    # invoice_status reflects the PO as a whole: "Booked" only once
                    # every GRN under this PO has its own invoice booked, otherwise
                    # "Partially Booked" — so remaining GRNs stay bookable.
                    total_grns = int(scalar("SELECT COUNT(*) FROM goods_receipts WHERE po_no=?", (po_no,), default=0))
                    invoiced_grns = int(scalar("SELECT COUNT(DISTINCT grn_no) FROM supplier_invoices WHERE po_no=?", (po_no,), default=0))
                    new_invoice_status = "Booked" if total_grns > 0 and invoiced_grns >= total_grns else "Partially Booked"
                    execute(
                        "UPDATE purchase_orders SET invoice_status=? WHERE po_no=?",
                        (new_invoice_status, po_no)
                    )
                    st.success(f"Invoice {supplier_invoice_no.strip()} booked successfully.")
                    st.rerun()

        st.markdown("### Supplier Invoice Register")
        st.dataframe(
            query("""SELECT invoice_id,invoice_no,invoice_date,po_no,grn_no,
                            supplier_name,subtotal,vat_amount,total_amount,
                            due_date,booked_by,status,payment_status,paid_amount
                     FROM supplier_invoices ORDER BY booked_at DESC"""),
            use_container_width=True,
            hide_index=True
        )

    with tab6:
        st.subheader("Invoice Payments")
        st.caption(
            "Payments are tracked per supplier invoice, not per PO — a PO with several "
            "GRN invoices can have each one paid independently."
        )

        payable=query("""
            SELECT invoice_id, invoice_no, invoice_date, po_no, grn_no, supplier_name,
                   total_amount, due_date, COALESCE(payment_status,'Unpaid') AS payment_status,
                   COALESCE(paid_amount,0) AS paid_amount, payment_reference, paid_at
            FROM supplier_invoices
            WHERE COALESCE(payment_status,'Unpaid') != 'Paid'
            ORDER BY supplier_name, due_date, invoice_no
        """)

        if payable.empty:
            st.info("No booked supplier invoices are awaiting payment.")
        else:
            vendors=sorted(payable["supplier_name"].dropna().unique().tolist())
            selected_vendor=st.selectbox(
                "Select Vendor",
                vendors
            )

            vendor_payable=payable[
                payable["supplier_name"]==selected_vendor
            ].copy()

            vendor_payable["outstanding_amount"] = (
                vendor_payable["total_amount"].astype(float)
                - vendor_payable["paid_amount"].fillna(0).astype(float)
            )

            st.dataframe(
                vendor_payable[[
                    "invoice_no","po_no","grn_no","supplier_name","due_date","total_amount",
                    "payment_status","paid_amount","outstanding_amount"
                ]],
                use_container_width=True,
                hide_index=True
            )

            vendor_payable["payment_label"]=vendor_payable.apply(
                lambda r: (
                    f"Inv {r['invoice_no']} | PO {r['po_no']} | GRN {r['grn_no']} | "
                    f"Outstanding {money(r['outstanding_amount'])}"
                ),
                axis=1
            )

            selected_labels=st.multiselect(
                "Select Multiple Invoices for Payment",
                vendor_payable["payment_label"].tolist()
            )

            # Matched on the full label (which encodes invoice_id-unique info)
            # rather than splitting a string — avoids any ambiguity between
            # invoices that share the same PO or GRN prefix.
            selected_rows=vendor_payable[
                vendor_payable["payment_label"].isin(selected_labels)
            ]

            selected_total=float(
                selected_rows["outstanding_amount"].sum()
            ) if not selected_rows.empty else 0.0

            c1,c2,c3=st.columns(3)
            c1.metric("Selected Vendor",selected_vendor)
            c2.metric("Selected Invoices",len(selected_rows))
            c3.metric("Total Outstanding",money(selected_total))

            payment_method=st.selectbox(
                "Payment Method",
                ["Bank Transfer","Cash","Cheque","Card"]
            )

            payment_reference=st.text_input(
                "Payment Reference / Bank Transaction No."
            )

            if selected_total > 0:
                payment_amount=st.number_input(
                    "Total Payment Amount",
                    min_value=0.01,
                    max_value=float(selected_total),
                    value=float(selected_total)
                )
            else:
                payment_amount=0.0
                st.number_input(
                    "Total Payment Amount",
                    min_value=0.0,
                    value=0.0,
                    disabled=True
                )

            st.caption(
                "The payment will be allocated automatically to the selected invoices "
                "in due-date order."
            )

            if st.button(
                "Record Invoice Payment",
                type="primary",
                disabled=(selected_total <= 0)
            ):
                remaining=float(payment_amount)
                paid_items=[]
                touched_po_nos=set()

                allocation_rows=selected_rows.sort_values(
                    ["due_date","invoice_no"]
                )

                for _, inv_row in allocation_rows.iterrows():
                    if remaining <= 0:
                        break

                    outstanding=float(inv_row["outstanding_amount"])
                    allocated=min(remaining,outstanding)
                    new_paid=float(inv_row["paid_amount"] or 0)+allocated

                    if abs(new_paid-float(inv_row["total_amount"])) < 0.01:
                        new_status="Paid"
                    else:
                        new_status="Partially Paid"

                    now=datetime.now().isoformat(timespec="seconds")
                    execute(
                        """UPDATE supplier_invoices
                           SET paid_amount=?,payment_status=?,payment_reference=?,paid_at=?
                           WHERE invoice_id=?""",
                        (
                            new_paid,
                            new_status,
                            payment_reference.strip(),
                            now,
                            inv_row["invoice_id"]
                        )
                    )

                    paid_items.append(
                        f"{inv_row['invoice_no']}:{allocated:.2f}"
                    )
                    touched_po_nos.add(inv_row["po_no"])
                    remaining-=allocated

                for touched_po in touched_po_nos:
                    sync_po_payment_rollup(touched_po)

                pid=next_code("PAY","payments")
                reference_text=payment_reference.strip() or ", ".join(paid_items)

                execute(
                    "INSERT INTO payments VALUES(?,?,?,?,?,?,?)",
                    (
                        pid,
                        datetime.now().isoformat(timespec="seconds"),
                        reference_text,
                        selected_vendor,
                        payment_method,
                        float(payment_amount),
                        "Vendor Invoice Payment"
                    )
                )

                st.success(
                    f"Payment of {money(payment_amount)} recorded for "
                    f"{selected_vendor} across {len(paid_items)} invoice(s)."
                )
                st.rerun()

    with tab7:
        st.subheader("Cancel Purchase Order")

        all_pos=query("""
            SELECT
                po_no,po_date,supplier_name,item_name,qty,total,status,
                grn_no,invoice_status,payment_status,paid_amount,
                cancelled_by,cancelled_at,cancellation_reason
            FROM purchase_orders
            ORDER BY po_no DESC
        """)

        if all_pos.empty:
            st.info("No purchase orders available.")
        else:
            st.dataframe(
                all_pos,
                use_container_width=True,
                hide_index=True
            )

            active_pos=all_pos[all_pos["status"]!="Cancelled"]

            if active_pos.empty:
                st.info("All purchase orders are already cancelled.")
            else:
                selected_po=st.selectbox(
                    "Select PO",
                    active_pos["po_no"].tolist(),
                    key="cancel_po_select"
                )
                row=active_pos[active_pos["po_no"]==selected_po].iloc[0]

                has_grn=bool(str(row["grn_no"] or "").strip())
                invoice_booked=str(row["invoice_status"] or "") in ["Booked","Partially Booked"]
                paid_amount=float(row["paid_amount"] or 0)
                payment_done=paid_amount > 0 or str(row["payment_status"] or "") in ["Partially Paid","Paid"]
                received_status=str(row["status"]) in ["Partially Received","Received"]

                c1,c2,c3,c4=st.columns(4)
                c1.metric("PO Status",str(row["status"]))
                c2.metric("GRN",str(row["grn_no"] or "Not Created"))
                c3.metric("Invoice",str(row["invoice_status"] or "Not Booked"))
                c4.metric("Paid Amount",money(paid_amount))

                cancellation_reason=st.text_area(
                    "Cancellation Reason",
                    placeholder="Enter the business reason for cancelling this PO."
                )

                blocked_reasons=[]
                if has_grn or received_status:
                    blocked_reasons.append("GRN/stock receipt exists")
                if invoice_booked:
                    blocked_reasons.append("supplier invoice is booked")
                if payment_done:
                    blocked_reasons.append("supplier payment exists")

                if blocked_reasons:
                    st.error(
                        "This PO cannot be cancelled directly because " +
                        ", ".join(blocked_reasons) +
                        ". Reverse the related transaction first."
                    )
                    st.button(
                        "Cancel PO",
                        disabled=True,
                        key="cancel_po_disabled"
                    )
                else:
                    st.warning(
                        "Cancelling the PO will stop approval, receipt, invoice booking, and payment processing."
                    )
                    confirm_cancel=st.checkbox(
                        f"I confirm cancellation of {selected_po}.",
                        key="confirm_po_cancel"
                    )

                    if st.button(
                        "Cancel PO",
                        type="primary",
                        disabled=not confirm_cancel,
                        key="cancel_po_button"
                    ):
                        if not cancellation_reason.strip():
                            st.error("Cancellation reason is required.")
                        else:
                            execute(
                                """UPDATE purchase_orders
                                   SET status='Cancelled',
                                       cancelled_by=?,
                                       cancelled_at=?,
                                       cancellation_reason=?
                                   WHERE po_no=?""",
                                (
                                    user["full_name"],
                                    datetime.now().isoformat(timespec="seconds"),
                                    cancellation_reason.strip(),
                                    selected_po
                                )
                            )
                            st.success(f"{selected_po} cancelled successfully.")
                            st.rerun()

        st.markdown("### Cancelled PO Register")
        cancelled=query("""
            SELECT po_no,po_date,supplier_name,item_name,total,
                   cancelled_by,cancelled_at,cancellation_reason
            FROM purchase_orders
            WHERE status='Cancelled'
            ORDER BY cancelled_at DESC
        """)
        st.dataframe(cancelled,use_container_width=True,hide_index=True)


    with tab8:
        st.subheader("Procurement Analytics & Three-Way Match")
        c1,c2,c3 = st.columns(3)
        from_date = c1.date_input("From Date", date.today()-timedelta(days=90), key="proc_from")
        to_date = c2.date_input("To Date", date.today(), key="proc_to")
        supplier_list = ["All"] + sorted(po_all["supplier_name"].dropna().unique().tolist()) if not po_all.empty else ["All"]
        supplier_filter = c3.selectbox("Supplier", supplier_list, key="proc_supplier")

        po_period = date_range_filter(po_all, "po_date", from_date, to_date)
        if supplier_filter != "All" and not po_period.empty:
            po_period = po_period[po_period["supplier_name"] == supplier_filter]

        if not po_period.empty:
            supplier_spend = po_period.groupby("supplier_name", as_index=False)["total"].sum().sort_values("total", ascending=False)
            st.markdown("### Supplier Spend")
            st.bar_chart(supplier_spend.set_index("supplier_name"))

        po_match = po_period[["po_no","po_date","supplier_name","item_name","qty","unit_cost","total","status"]].copy() if not po_period.empty else pd.DataFrame()
        grn_match = grn_all[["grn_no","po_no","received_qty","rejected_qty","accepted_qty","status"]].copy() if not grn_all.empty else pd.DataFrame()
        invoice_match = inv_all[["invoice_id","invoice_no","invoice_date","po_no","grn_no","subtotal","vat_amount","total_amount","paid_amount","payment_status"]].copy() if not inv_all.empty else pd.DataFrame()

        if not po_match.empty:
            if not grn_match.empty:
                grn_summary = grn_match.groupby("po_no", as_index=False).agg(
                    grn_count=("grn_no","count"),
                    received_qty=("received_qty","sum"),
                    rejected_qty=("rejected_qty","sum"),
                    accepted_qty=("accepted_qty","sum")
                )
                match = po_match.merge(grn_summary, on="po_no", how="left")
            else:
                match = po_match.copy()
                match[["grn_count","received_qty","rejected_qty","accepted_qty"]] = 0

            if not invoice_match.empty:
                inv_summary = invoice_match.groupby("po_no", as_index=False).agg(
                    invoice_count=("invoice_id","count"),
                    invoiced_total=("total_amount","sum"),
                    paid_total=("paid_amount","sum")
                )
                match = match.merge(inv_summary, on="po_no", how="left")
            else:
                match[["invoice_count","invoiced_total","paid_total"]] = 0

            for col in ["grn_count","received_qty","rejected_qty","accepted_qty","invoice_count","invoiced_total","paid_total"]:
                if col not in match.columns:
                    match[col] = 0
                match[col] = match[col].fillna(0)

            match["quantity_variance"] = match["qty"] - match["accepted_qty"]
            match["invoice_variance"] = match["total"] - match["invoiced_total"]
            match["open_payable"] = (match["invoiced_total"] - match["paid_total"]).clip(lower=0)
            match["match_status"] = match.apply(
                lambda r: "MATCHED" if abs(float(r["quantity_variance"])) < 0.0001 and abs(float(r["invoice_variance"])) <= 1.0
                else "REVIEW", axis=1
            )

            m1,m2,m3,m4 = st.columns(4)
            m1.metric("POs Reviewed", len(match))
            m2.metric("Fully Matched", int((match["match_status"]=="MATCHED").sum()))
            m3.metric("Requires Review", int((match["match_status"]=="REVIEW").sum()))
            m4.metric("Open Payable", money(match["open_payable"].sum()))

            st.dataframe(match, use_container_width=True, hide_index=True, height=430)
            exceptions = match[match["match_status"]=="REVIEW"].copy()
            st.download_button(
                "Export Procurement Control Pack",
                data=excel_file({
                    "Three Way Match": match,
                    "Exceptions": exceptions,
                    "Purchase Orders": po_period,
                    "Goods Receipts": grn_all,
                    "Supplier Invoices": inv_all
                }),
                file_name=f"Procurement_Control_Pack_{from_date}_{to_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        else:
            st.info("No purchase orders found for the selected period.")

# ---------------- Maintenance ----------------
elif page == "Maintenance":
    st.title("Maintenance")
    rooms=query("SELECT room_no FROM rooms")
    with st.form("maintenance"):
        c1,c2=st.columns(2)
        room=c1.selectbox("Room",rooms["room_no"].tolist())
        priority=c2.selectbox("Priority",["Low","Medium","High","Critical"])
        issue=st.text_area("Issue")
        assigned=st.text_input("Assigned To")
        submit=st.form_submit_button("Create Ticket")
    if submit and issue:
        tid=next_code("MNT","maintenance")
        execute("INSERT INTO maintenance VALUES(?,?,?,?,?,?,?)",
                (tid,room,issue,priority,assigned,"Open",datetime.now().isoformat(timespec="seconds")))
        st.success("Ticket created."); st.rerun()
    df=query("SELECT * FROM maintenance ORDER BY created_at DESC")
    st.dataframe(df,use_container_width=True,hide_index=True)
    if not df.empty:
        tid=st.selectbox("Ticket",df["ticket_id"].tolist())
        status=st.selectbox("Update Status",["Open","In Progress","Closed"])
        if st.button("Update Ticket"):
            execute("UPDATE maintenance SET status=? WHERE ticket_id=?",(status,tid))
            st.success("Ticket updated."); st.rerun()

# ---------------- Payments / Expenses ----------------
elif page == "Payments":
    st.title("Payments")
    df=query("SELECT * FROM payments ORDER BY payment_date DESC")
    st.dataframe(df,use_container_width=True,hide_index=True)
    if not df.empty:
        st.bar_chart(df.groupby("payment_method")["amount"].sum())

elif page == "Expenses":
    st.title("Expenses")
    with st.form("expense"):
        c1,c2=st.columns(2)
        exp_date=c1.date_input("Date",date.today())
        category=c2.selectbox("Category",["Food Purchase","Housekeeping","Maintenance","Utilities","Payroll","Other"])
        desc=st.text_input("Description")
        amount=st.number_input("Amount",0.0)
        submit=st.form_submit_button("Record Expense")
    if submit:
        eid=next_code("EXP","expenses")
        execute("INSERT INTO expenses VALUES(?,?,?,?,?)",(eid,str(exp_date),category,desc,amount))
        st.success("Expense recorded."); st.rerun()
    st.dataframe(query("SELECT * FROM expenses ORDER BY expense_date DESC"),use_container_width=True,hide_index=True)

# ---------------- Finance Control Tower ----------------
elif page == "Finance Control Tower":
    st.title("Finance Control Tower")
    st.markdown("<div class='demo-banner'>Enterprise finance workspace • Daily control • General ledger • AP/AR • Treasury • Budget and management reporting</div>", unsafe_allow_html=True)

    room_rev = scalar("""SELECT SUM(MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate)
                         FROM reservations WHERE status IN ('Checked-in','Checked-out')""")
    restaurant_rev = scalar("SELECT SUM(amount) FROM orders WHERE status NOT IN ('Cancelled','Void')")
    collections = scalar("SELECT SUM(amount) FROM payments")
    operating_expenses = scalar("SELECT SUM(amount) FROM expenses")
    purchases = scalar("SELECT SUM(total) FROM purchase_orders WHERE status NOT IN ('Cancelled','Rejected')")
    supplier_due = scalar("SELECT SUM(total_amount-COALESCE(paid_amount,0)) FROM supplier_invoices WHERE payment_status!='Paid'")
    receivable = max(float(room_rev or 0) + float(restaurant_rev or 0) - float(collections or 0), 0)
    net_result = float(room_rev or 0) + float(restaurant_rev or 0) - float(operating_expenses or 0) - float(purchases or 0)
    business_date = scalar("SELECT setting_value FROM finance_settings WHERE setting_key='business_date'", default=str(date.today()))

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Total Revenue", money(float(room_rev or 0)+float(restaurant_rev or 0)))
    k2.metric("Collections", money(collections))
    k3.metric("Accounts Receivable", money(receivable))
    k4.metric("Accounts Payable", money(supplier_due))
    k5.metric("Net Result", money(net_result))
    k6.metric("Business Date", str(business_date))

    tab_dash, tab_date, tab_gl, tab_budget, tab_apar, tab_treasury, tab_reports = st.tabs([
        "Executive Dashboard","Business Date & Period","General Ledger","Budget vs Actual",
        "AP / AR","Treasury","Financial Reports"
    ])

    with tab_dash:
        c1,c2 = st.columns(2)
        with c1:
            rev_df = pd.DataFrame([
                ["Room Revenue", float(room_rev or 0)],
                ["Restaurant Revenue", float(restaurant_rev or 0)],
                ["Collections", float(collections or 0)]
            ], columns=["Category","Amount"])
            st.markdown("### Revenue and Collections")
            st.bar_chart(rev_df.set_index("Category"))
        with c2:
            cost_df = pd.DataFrame([
                ["Purchases", float(purchases or 0)],
                ["Operating Expenses", float(operating_expenses or 0)],
                ["Supplier Due", float(supplier_due or 0)]
            ], columns=["Category","Amount"])
            st.markdown("### Cost and Liability Position")
            st.bar_chart(cost_df.set_index("Category"))

        st.markdown("### Finance Alerts")
        alerts=[]
        if supplier_due > 0: alerts.append(f"Supplier liabilities of {money(supplier_due)} require payment planning.")
        if receivable > 0: alerts.append(f"Uncollected guest and operational revenue is estimated at {money(receivable)}.")
        if net_result < 0: alerts.append(f"Current estimated result is negative by {money(abs(net_result))}; review purchasing and operating expenses.")
        if not alerts: alerts=["No critical finance exception detected from the available demo data."]
        for a in alerts: st.info(a)

    with tab_date:
        st.subheader("Business Date Control")
        c1,c2,c3 = st.columns(3)
        current_bd = pd.to_datetime(business_date).date() if business_date else date.today()
        new_bd = c1.date_input("Business Date", current_bd)
        period_lock = scalar("SELECT setting_value FROM finance_settings WHERE setting_key='period_lock'", default='')
        lock_month = c2.text_input("Locked Period (YYYY-MM)", value=str(period_lock or ''), placeholder="Example: 2026-07")
        c3.metric("Current Status", "Locked" if period_lock else "Open")
        c1,c2,c3 = st.columns(3)
        if c1.button("Update Business Date", type="primary"):
            execute("UPDATE finance_settings SET setting_value=?, updated_by=?, updated_at=? WHERE setting_key='business_date'",
                    (str(new_bd), user['username'], datetime.now().isoformat(timespec='seconds')))
            st.success("Business date updated."); st.rerun()
        if c2.button("Lock Period"):
            if re.match(r'^\\d{4}-\\d{2}$', lock_month.strip()):
                execute("UPDATE finance_settings SET setting_value=?, updated_by=?, updated_at=? WHERE setting_key='period_lock'",
                        (lock_month.strip(), user['username'], datetime.now().isoformat(timespec='seconds')))
                st.success("Period locked."); st.rerun()
            else: st.error("Enter period in YYYY-MM format.")
        if c3.button("Re-open Period"):
            if user['role'] != 'Admin': st.error("Only Admin can reopen a period.")
            else:
                execute("UPDATE finance_settings SET setting_value='', updated_by=?, updated_at=? WHERE setting_key='period_lock'",
                        (user['username'], datetime.now().isoformat(timespec='seconds')))
                st.success("Period reopened."); st.rerun()

        st.markdown("### Daily Closing Checklist")
        checklist = pd.DataFrame([
            ["Front office folios reviewed", "Pending"],
            ["Restaurant sales closed", "Pending"],
            ["Cash and card collections reconciled", "Pending"],
            ["Supplier invoices reviewed", "Pending"],
            ["Inventory movements posted", "Pending"],
            ["Management report generated", "Pending"],
        ], columns=["Control","Status"])
        st.dataframe(checklist, use_container_width=True, hide_index=True)

    with tab_gl:
        st.subheader("General Ledger")
        coa_tab, journal_tab, inquiry_tab = st.tabs(["Chart of Accounts","New Journal","Journal Inquiry"])
        with coa_tab:
            coa=query("SELECT * FROM chart_of_accounts ORDER BY account_code")
            st.dataframe(coa,use_container_width=True,hide_index=True)
            with st.form("new_coa"):
                c1,c2,c3=st.columns(3)
                code=c1.text_input("Account Code")
                name=c2.text_input("Account Name")
                acc_type=c3.selectbox("Account Type",["Asset","Liability","Equity","Revenue","Expense"])
                parent=st.text_input("Parent Code (optional)")
                save_coa=st.form_submit_button("Add Account")
            if save_coa:
                try:
                    execute("INSERT INTO chart_of_accounts VALUES(?,?,?,?,1)",(code.strip(),name.strip(),acc_type,parent.strip() or None))
                    st.success("Account added."); st.rerun()
                except Exception as e: st.error(f"Could not add account: {e}")

        with journal_tab:
            coa=query("SELECT account_code,account_name FROM chart_of_accounts WHERE is_active=1 ORDER BY account_code")
            labels={f"{r.account_code} - {r.account_name}":r.account_code for r in coa.itertuples()}
            with st.form("journal_form"):
                c1,c2=st.columns(2)
                jdate=c1.date_input("Journal Date", pd.to_datetime(business_date).date() if business_date else date.today())
                reference=c2.text_input("Reference")
                description=st.text_input("Description")
                st.caption("Enter one debit line and one credit line. Additional complex journals can be extended later.")
                c1,c2,c3=st.columns(3)
                debit_label=c1.selectbox("Debit Account",list(labels.keys()),key="debit_acc")
                credit_label=c2.selectbox("Credit Account",list(labels.keys()),key="credit_acc")
                amount=c3.number_input("Amount",min_value=0.0,step=100.0)
                department=st.selectbox("Department",["Front Office","Restaurant","Housekeeping","Maintenance","Administration","General"])
                post=st.form_submit_button("Create Journal",type="primary")
            if post:
                locked = bool(period_lock and str(jdate)[:7] <= str(period_lock))
                if locked: st.error(f"Period {str(jdate)[:7]} is locked.")
                elif amount <= 0: st.error("Amount must be greater than zero.")
                else:
                    jno=next_code("JV","journal_headers")
                    execute("INSERT INTO journal_headers VALUES(?,?,?,?,?,?,?,?,?)",
                            (jno,str(jdate),reference,description,"Posted",user['username'],datetime.now().isoformat(timespec='seconds'),user['username'],datetime.now().isoformat(timespec='seconds')))
                    execute("INSERT INTO journal_lines(journal_no,account_code,department,debit,credit,narration) VALUES(?,?,?,?,?,?)",
                            (jno,labels[debit_label],department,amount,0,description))
                    execute("INSERT INTO journal_lines(journal_no,account_code,department,debit,credit,narration) VALUES(?,?,?,?,?,?)",
                            (jno,labels[credit_label],department,0,amount,description))
                    st.success(f"Journal {jno} posted."); st.rerun()

        with inquiry_tab:
            journals=query("""SELECT h.journal_no,h.journal_date,h.reference,h.description,h.status,h.created_by,
                               SUM(l.debit) AS total_debit,SUM(l.credit) AS total_credit
                               FROM journal_headers h LEFT JOIN journal_lines l ON h.journal_no=l.journal_no
                               GROUP BY h.journal_no ORDER BY h.journal_date DESC,h.journal_no DESC""")
            st.dataframe(journals,use_container_width=True,hide_index=True)
            if not journals.empty:
                sel=st.selectbox("View Journal",journals['journal_no'].tolist())
                st.dataframe(query("SELECT * FROM journal_lines WHERE journal_no=?",(sel,)),use_container_width=True,hide_index=True)

    with tab_budget:
        st.subheader("Budget vs Actual")
        year=st.number_input("Fiscal Year",min_value=2020,max_value=2100,value=date.today().year,step=1)
        with st.form("budget_form"):
            c1,c2,c3,c4=st.columns(4)
            month=c1.selectbox("Month",list(range(1,13)),index=date.today().month-1)
            dept=c2.selectbox("Department",["Front Office","Restaurant","Housekeeping","Maintenance","Administration","General"])
            acc_df=query("SELECT account_code,account_name FROM chart_of_accounts WHERE account_type IN ('Revenue','Expense') ORDER BY account_code")
            acc_labels={f"{r.account_code} - {r.account_name}":r.account_code for r in acc_df.itertuples()}
            acc_label=c3.selectbox("Account",list(acc_labels.keys()))
            budget_amt=c4.number_input("Budget Amount",min_value=0.0,step=1000.0)
            save_budget=st.form_submit_button("Save Budget")
        if save_budget:
            execute("""INSERT INTO budgets(fiscal_year,month_no,department,account_code,budget_amount)
                       VALUES(?,?,?,?,?)
                       ON CONFLICT(fiscal_year,month_no,department,account_code)
                       DO UPDATE SET budget_amount=excluded.budget_amount""",
                    (int(year),int(month),dept,acc_labels[acc_label],budget_amt))
            st.success("Budget saved."); st.rerun()

        budgets=query("""SELECT b.fiscal_year,b.month_no,b.department,b.account_code,c.account_name,b.budget_amount
                         FROM budgets b LEFT JOIN chart_of_accounts c ON b.account_code=c.account_code
                         WHERE b.fiscal_year=? ORDER BY b.month_no,b.department,b.account_code""",(int(year),))
        if budgets.empty:
            st.info("No budget entered for the selected year.")
        else:
            actual_room=float(room_rev or 0); actual_rest=float(restaurant_rev or 0); actual_exp=float(operating_expenses or 0)+float(purchases or 0)
            def actual_for(code):
                return actual_room if code=='4000' else actual_rest if code=='4100' else actual_exp if str(code).startswith(('5','6')) else 0.0
            budgets['actual_amount']=budgets['account_code'].apply(actual_for)
            budgets['variance']=budgets['actual_amount']-budgets['budget_amount']
            budgets['variance_pct']=budgets.apply(lambda r: (r['variance']/r['budget_amount']*100) if r['budget_amount'] else 0,axis=1)
            st.dataframe(budgets,use_container_width=True,hide_index=True)
            st.download_button("Export Budget vs Actual",excel_file({"Budget vs Actual":budgets}),f"Budget_vs_Actual_{year}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab_apar:
        st.subheader("Accounts Payable and Accounts Receivable")
        ap=query("""SELECT invoice_no,po_no,supplier_name AS supplier,invoice_date,total_amount,COALESCE(paid_amount,0) paid_amount,
                    total_amount-COALESCE(paid_amount,0) outstanding,payment_status
                    FROM supplier_invoices ORDER BY invoice_date DESC""")
        ar=query("""SELECT reservation_id,guest_name,room_no,checkin_date,checkout_date,room_rate,deposit,status,
                    MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate AS room_charge,
                    MAX(MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate-deposit,0) AS outstanding
                    FROM reservations WHERE status IN ('Reserved','Checked-in','Checked-out') ORDER BY checkin_date DESC""")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("### AP Aging")
            st.dataframe(ap,use_container_width=True,hide_index=True,height=380)
        with c2:
            st.markdown("### AR / Guest Folio Aging")
            st.dataframe(ar,use_container_width=True,hide_index=True,height=380)
        st.download_button("Export AP & AR Pack",excel_file({"Accounts Payable":ap,"Accounts Receivable":ar}),"AP_AR_Control_Pack.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")

    with tab_treasury:
        st.subheader("Treasury and Bank Position")
        bank_df=query("SELECT * FROM bank_accounts WHERE is_active=1 ORDER BY bank_code")
        tx=query("SELECT * FROM bank_transactions ORDER BY transaction_date DESC,created_at DESC")
        tx_balance=float(tx.apply(lambda r: r['amount'] if r['transaction_type']=='Receipt' else -r['amount'],axis=1).sum()) if not tx.empty else 0
        opening=float(bank_df['opening_balance'].sum()) if not bank_df.empty else 0
        c1,c2,c3=st.columns(3)
        c1.metric("Opening Bank Balance",money(opening))
        c2.metric("Net Bank Movement",money(tx_balance))
        c3.metric("Estimated Bank Balance",money(opening+tx_balance))
        with st.form("bank_tx_form"):
            c1,c2,c3=st.columns(3)
            bank_code=c1.selectbox("Bank",bank_df['bank_code'].tolist() if not bank_df.empty else ['BANK-001'])
            tx_date=c2.date_input("Transaction Date",date.today())
            tx_type=c3.selectbox("Type",["Receipt","Payment"])
            c1,c2,c3=st.columns(3)
            tx_ref=c1.text_input("Reference")
            tx_desc=c2.text_input("Description")
            tx_amt=c3.number_input("Amount",min_value=0.0,step=100.0,key="bank_amt")
            save_tx=st.form_submit_button("Record Bank Transaction")
        if save_tx and tx_amt>0:
            txid=next_code("BTX","bank_transactions")
            execute("INSERT INTO bank_transactions VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (txid,bank_code,str(tx_date),tx_type,tx_ref,tx_desc,tx_amt,0,user['username'],datetime.now().isoformat(timespec='seconds')))
            st.success("Bank transaction recorded."); st.rerun()
        st.dataframe(tx,use_container_width=True,hide_index=True)

    with tab_reports:
        st.subheader("Financial Statements and Compliance Pack")
        pnl=pd.DataFrame([
            ["Room Revenue",float(room_rev or 0)],
            ["Restaurant Revenue",float(restaurant_rev or 0)],
            ["Total Revenue",float(room_rev or 0)+float(restaurant_rev or 0)],
            ["Purchases",-float(purchases or 0)],
            ["Operating Expenses",-float(operating_expenses or 0)],
            ["Estimated Net Result",net_result]
        ],columns=["Line","Amount"])
        trial=query("""SELECT l.account_code,c.account_name,c.account_type,SUM(l.debit) debit,SUM(l.credit) credit,
                       SUM(l.debit-l.credit) balance
                       FROM journal_lines l LEFT JOIN chart_of_accounts c ON l.account_code=c.account_code
                       GROUP BY l.account_code,c.account_name,c.account_type ORDER BY l.account_code""")
        vat_output=(float(room_rev or 0)+float(restaurant_rev or 0))*15/115
        vat_input=(float(purchases or 0)+float(operating_expenses or 0))*15/115
        vat=pd.DataFrame([["Output VAT",vat_output],["Estimated Input VAT",vat_input],["Net VAT Payable",vat_output-vat_input]],columns=["VAT Line","Amount"])
        c1,c2=st.columns(2)
        with c1:
            st.markdown("### Profit & Loss")
            st.dataframe(pnl,use_container_width=True,hide_index=True)
        with c2:
            st.markdown("### VAT Summary")
            st.dataframe(vat,use_container_width=True,hide_index=True)
        st.markdown("### Trial Balance")
        st.dataframe(trial,use_container_width=True,hide_index=True)
        st.download_button("Download Finance Control Pack",excel_file({"Profit and Loss":pnl,"Trial Balance":trial,"VAT Summary":vat,"AP":ap,"AR":ar,"Bank Transactions":tx}),"Hotel_Finance_Control_Pack.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")

# ---------------- AI Executive Command Center ----------------
elif page == "AI Command Center":
    st.title("AI Executive Command Center")
    st.markdown(
        """<div class="ai-command-banner">
        <div><div class="ai-command-title">Cross-Module Intelligence Cockpit</div>
        <div class="ai-command-sub">Live operational, financial and guest-experience signals from the complete hotel platform.</div></div>
        <div class="ai-live-chip">● LIVE ANALYTICS</div></div>""",
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns([1,1,1])
    analysis_from = c1.date_input("Analysis From", date.today()-timedelta(days=30), key="ai_from")
    analysis_to = c2.date_input("Analysis To", date.today(), key="ai_to")
    compare_mode = c3.selectbox("Comparison", ["Previous equal period", "No comparison"], key="ai_compare")
    if analysis_to < analysis_from:
        st.error("Analysis To date must be on or after Analysis From date.")
        st.stop()

    start_s, end_s = str(analysis_from), str(analysis_to)
    period_days = (analysis_to-analysis_from).days + 1
    prev_to = analysis_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=period_days-1)

    rooms_total = int(scalar("SELECT COUNT(*) FROM rooms", default=0) or 0)
    rooms_occupied = int(scalar("SELECT COUNT(*) FROM rooms WHERE status='Occupied'", default=0) or 0)
    rooms_available = int(scalar("SELECT COUNT(*) FROM rooms WHERE status='Available'", default=0) or 0)
    occupancy = (rooms_occupied / rooms_total * 100) if rooms_total else 0.0

    room_revenue = float(scalar("""SELECT COALESCE(SUM(MAX(julianday(MIN(checkout_date,?))-julianday(MAX(checkin_date,?)),0)*room_rate),0)
                                  FROM reservations
                                  WHERE status IN ('Reserved','Checked-in','Checked-out')
                                  AND checkout_date>=? AND checkin_date<=?""",
                                (end_s,start_s,start_s,end_s),0) or 0)
    restaurant_revenue = float(scalar("SELECT COALESCE(SUM(amount),0) FROM orders WHERE date(order_time) BETWEEN ? AND ? AND status!='Cancelled'", (start_s,end_s),0) or 0)
    collections = float(scalar("SELECT COALESCE(SUM(amount),0) FROM payments WHERE date(payment_date) BETWEEN ? AND ?", (start_s,end_s),0) or 0)
    expenses_total = float(scalar("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE date(expense_date) BETWEEN ? AND ?", (start_s,end_s),0) or 0)
    purchases_total = float(scalar("SELECT COALESCE(SUM(total),0) FROM purchase_orders WHERE date(po_date) BETWEEN ? AND ? AND status!='Cancelled'", (start_s,end_s),0) or 0)
    total_revenue = room_revenue + restaurant_revenue
    estimated_result = total_revenue - expenses_total - purchases_total
    open_ap = float(scalar("SELECT COALESCE(SUM(total_amount-COALESCE(paid_amount,0)),0) FROM supplier_invoices", default=0) or 0)
    pending_approvals = int(scalar("SELECT COUNT(*) FROM purchase_orders WHERE status LIKE 'Pending%'", default=0) or 0)
    low_stock = int(scalar("SELECT COUNT(*) FROM inventory WHERE (opening_qty+received_qty-issued_qty)<=reorder_level", default=0) or 0)
    open_maintenance = int(scalar("SELECT COUNT(*) FROM maintenance WHERE status NOT IN ('Completed','Closed')", default=0) or 0)
    delayed_kitchen = int(scalar("""SELECT COUNT(*) FROM orders
                                   WHERE status IN ('Pending','Preparing')
                                   AND (julianday('now')-julianday(order_time))*1440 > COALESCE(target_minutes,15)""", default=0) or 0)

    prev_total = 0.0
    if compare_mode == "Previous equal period":
        pr = float(scalar("""SELECT COALESCE(SUM(MAX(julianday(MIN(checkout_date,?))-julianday(MAX(checkin_date,?)),0)*room_rate),0)
                             FROM reservations WHERE status IN ('Reserved','Checked-in','Checked-out')
                             AND checkout_date>=? AND checkin_date<=?""",
                          (str(prev_to),str(prev_from),str(prev_from),str(prev_to)),0) or 0)
        prest = float(scalar("SELECT COALESCE(SUM(amount),0) FROM orders WHERE date(order_time) BETWEEN ? AND ? AND status!='Cancelled'", (str(prev_from),str(prev_to)),0) or 0)
        prev_total = pr + prest
    revenue_delta = ((total_revenue-prev_total)/prev_total*100) if prev_total else 0.0

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total Revenue", money(total_revenue), f"{revenue_delta:+.1f}%" if prev_total else None)
    k2.metric("Occupancy", f"{occupancy:.1f}%", f"{rooms_occupied}/{rooms_total} rooms")
    k3.metric("Collections", money(collections))
    k4.metric("Estimated Result", money(estimated_result))
    k5.metric("Open Payables", money(open_ap))

    st.markdown("<div class='exec-section-label'>Executive intelligence</div>", unsafe_allow_html=True)
    insights = []
    if prev_total:
        if revenue_delta >= 5:
            insights.append(("good","Revenue Momentum",f"Revenue is {revenue_delta:.1f}% above the previous equal period."))
        elif revenue_delta <= -5:
            insights.append(("risk","Revenue Risk",f"Revenue is {abs(revenue_delta):.1f}% below the previous equal period. Review occupancy, rates and restaurant demand."))
        else:
            insights.append(("","Stable Revenue",f"Revenue changed by {revenue_delta:+.1f}% versus the previous equal period."))
    if occupancy >= 85:
        insights.append(("good","Strong Occupancy",f"Occupancy is {occupancy:.1f}%. Protect rate integrity and prioritize room turnaround."))
    elif occupancy < 55:
        insights.append(("warn","Occupancy Opportunity",f"Occupancy is {occupancy:.1f}%. Consider targeted offers and channel actions."))
    if delayed_kitchen:
        insights.append(("risk","Kitchen SLA Alert",f"{delayed_kitchen} active order line(s) exceeded the target preparation time."))
    if low_stock:
        insights.append(("warn","Stock Replenishment",f"{low_stock} inventory item(s) are at or below reorder level."))
    if pending_approvals:
        insights.append(("warn","Approval Bottleneck",f"{pending_approvals} purchase order(s) are waiting for approval."))
    if open_maintenance:
        insights.append(("risk" if open_maintenance>3 else "warn","Maintenance Exposure",f"{open_maintenance} maintenance ticket(s) remain open."))
    if open_ap > collections and open_ap > 0:
        insights.append(("warn","Liquidity Attention",f"Open supplier payables of {money(open_ap)} exceed collections in the selected period."))
    if not insights:
        insights.append(("good","Operations Stable","No major operating exception was detected from the available data."))

    left,right = st.columns([1.4,1])
    with left:
        for cls,title,copy in insights[:6]:
            st.markdown(f"<div class='ai-insight {cls}'><div class='ai-insight-title'>{title}</div><div class='ai-insight-copy'>{copy}</div></div>", unsafe_allow_html=True)
    with right:
        st.markdown("### Priority Alerts")
        alert_df = pd.DataFrame([
            ["Kitchen", delayed_kitchen, "High" if delayed_kitchen else "Normal"],
            ["Inventory", low_stock, "High" if low_stock>5 else "Medium" if low_stock else "Normal"],
            ["Approvals", pending_approvals, "High" if pending_approvals>5 else "Medium" if pending_approvals else "Normal"],
            ["Maintenance", open_maintenance, "High" if open_maintenance>3 else "Medium" if open_maintenance else "Normal"],
        ], columns=["Area","Open Items","Priority"])
        st.dataframe(alert_df, use_container_width=True, hide_index=True)

    st.markdown("<div class='exec-section-label'>Revenue and operating trends</div>", unsafe_allow_html=True)
    trend = query("""WITH RECURSIVE dates(d) AS (
                         SELECT date(?) UNION ALL SELECT date(d,'+1 day') FROM dates WHERE d < date(?)
                      ), room AS (
                         SELECT date(checkin_date) d, SUM(MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate) amount
                         FROM reservations WHERE date(checkin_date) BETWEEN date(?) AND date(?) GROUP BY date(checkin_date)
                      ), rest AS (
                         SELECT date(order_time) d, SUM(amount) amount FROM orders
                         WHERE date(order_time) BETWEEN date(?) AND date(?) AND status!='Cancelled' GROUP BY date(order_time)
                      )
                      SELECT dates.d AS business_date, COALESCE(room.amount,0) room_revenue,
                             COALESCE(rest.amount,0) restaurant_revenue,
                             COALESCE(room.amount,0)+COALESCE(rest.amount,0) total_revenue
                      FROM dates LEFT JOIN room ON room.d=dates.d LEFT JOIN rest ON rest.d=dates.d ORDER BY dates.d""",
                  (start_s,end_s,start_s,end_s,start_s,end_s))
    c1,c2 = st.columns([1.6,1])
    with c1:
        if not trend.empty:
            st.line_chart(trend.set_index("business_date")[["room_revenue","restaurant_revenue","total_revenue"]], use_container_width=True)
        else:
            st.info("No trend data is available for the selected period.")
    with c2:
        mix = pd.DataFrame({"Revenue Stream":["Rooms","Restaurant"],"Amount":[room_revenue,restaurant_revenue]}).set_index("Revenue Stream")
        st.bar_chart(mix, use_container_width=True)

    st.markdown("<div class='exec-section-label'>30-day predictive outlook</div>", unsafe_allow_html=True)
    hist = query("""SELECT business_date, SUM(total_revenue) total_revenue FROM (
                      SELECT date(checkin_date) business_date, MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate total_revenue
                      FROM reservations WHERE date(checkin_date)>=date('now','-89 day')
                      UNION ALL
                      SELECT date(order_time), amount FROM orders WHERE date(order_time)>=date('now','-89 day') AND status!='Cancelled'
                    ) GROUP BY business_date ORDER BY business_date""")
    forecast_rows=[]
    if not hist.empty:
        hist['business_date']=pd.to_datetime(hist['business_date'],errors='coerce')
        hist=hist.dropna(subset=['business_date']).sort_values('business_date')
        hist['x']=range(len(hist))
        n=len(hist)
        sx=float(hist['x'].sum()); sy=float(hist['total_revenue'].sum())
        sxx=float((hist['x']**2).sum()); sxy=float((hist['x']*hist['total_revenue']).sum())
        denom=n*sxx-sx*sx
        slope=(n*sxy-sx*sy)/denom if denom and n>1 else 0.0
        intercept=(sy-slope*sx)/n if n else 0.0
        base_date=hist['business_date'].max()
        for i in range(1,31):
            val=max(0.0,intercept+slope*(n-1+i))
            forecast_rows.append([(base_date+pd.Timedelta(days=i)).date(),val])
    forecast=pd.DataFrame(forecast_rows,columns=['forecast_date','forecast_revenue'])
    if not forecast.empty:
        f1,f2,f3 = st.columns(3)
        next_7=float(forecast.head(7)['forecast_revenue'].sum())
        next_30=float(forecast['forecast_revenue'].sum())
        f1.metric("Forecast — Next 7 Days", money(next_7))
        f2.metric("Forecast — Next 30 Days", money(next_30))
        f3.metric("Average Forecast / Day", money(next_30/30))
        st.line_chart(forecast.set_index('forecast_date'), use_container_width=True)
        st.markdown("<div class='forecast-note'>Forecast uses a simple linear trend based on up to 90 days of available room and restaurant revenue. It is an operational estimate, not an audited financial forecast.</div>", unsafe_allow_html=True)
    else:
        st.info("At least some historical revenue data is required to generate the forecast.")

    st.markdown("<div class='exec-section-label'>Ask the Hotel Copilot</div>", unsafe_allow_html=True)
    st.markdown("<div class='command-question'>Try: “What needs attention?”, “How is revenue?”, “Show occupancy”, “What is due to suppliers?”, or “How is the kitchen?”</div>", unsafe_allow_html=True)
    question = st.text_input("Ask a management question", placeholder="What should management focus on today?", key="copilot_question")
    if question.strip():
        q=question.lower()
        if any(x in q for x in ['attention','risk','alert','focus','problem']):
            answer = "Management priorities: " + "; ".join([copy for _,_,copy in insights[:4]])
        elif any(x in q for x in ['revenue','sales','income']):
            answer = f"Selected-period revenue is {money(total_revenue)}: rooms {money(room_revenue)} and restaurant {money(restaurant_revenue)}. Estimated result after purchases and operating expenses is {money(estimated_result)}."
        elif any(x in q for x in ['occupancy','rooms','available']):
            answer = f"Occupancy is {occupancy:.1f}% with {rooms_occupied} occupied, {rooms_available} available and {rooms_total} rooms in total."
        elif any(x in q for x in ['supplier','payable','ap','due']):
            answer = f"Open supplier payables are {money(open_ap)}. There are {pending_approvals} purchase orders waiting for approval."
        elif any(x in q for x in ['kitchen','restaurant','food']):
            answer = f"Restaurant revenue is {money(restaurant_revenue)} for the selected period. {delayed_kitchen} active order line(s) currently exceed target preparation time."
        elif any(x in q for x in ['stock','inventory','reorder']):
            answer = f"{low_stock} inventory item(s) are at or below reorder level and require review."
        elif any(x in q for x in ['maintenance','repair']):
            answer = f"There are {open_maintenance} open maintenance ticket(s)."
        else:
            answer = f"For {analysis_from} to {analysis_to}, revenue is {money(total_revenue)}, occupancy is {occupancy:.1f}%, collections are {money(collections)}, and estimated result is {money(estimated_result)}. Ask about revenue, occupancy, suppliers, kitchen, inventory or maintenance for more detail."
        st.success(answer)

    command_summary = pd.DataFrame([
        ["Analysis From", start_s], ["Analysis To", end_s], ["Total Revenue", total_revenue],
        ["Room Revenue", room_revenue], ["Restaurant Revenue", restaurant_revenue],
        ["Collections", collections], ["Estimated Result", estimated_result], ["Occupancy %", occupancy],
        ["Open Payables", open_ap], ["Pending Approvals", pending_approvals], ["Low Stock Items", low_stock],
        ["Open Maintenance", open_maintenance], ["Delayed Kitchen Orders", delayed_kitchen]
    ], columns=["KPI","Value"])
    insight_export = pd.DataFrame([[t,c] for _,t,c in insights], columns=["Insight","Detail"])
    export_sheets = {"Executive Summary":command_summary,"Insights":insight_export,"Alerts":alert_df,"Revenue Trend":trend,"Forecast":forecast}
    st.download_button("Download AI Executive Control Pack", excel_file(export_sheets), f"Hotel_AI_Executive_Control_Pack_{analysis_from}_{analysis_to}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

# ---------------- Reports ----------------
elif page == "Reports":
    st.title("Excel Export")
    sheets={
        "Rooms":query("SELECT * FROM rooms"),
        "Reservations":query("SELECT * FROM reservations"),
        "Orders":query("SELECT * FROM orders"),
        "Inventory":stock_df(),
        "Suppliers":query("SELECT * FROM suppliers"),
        "Purchase Orders":query("SELECT * FROM purchase_orders"),
        "Supplier Invoices":query("SELECT * FROM supplier_invoices"),
        "Payments":query("SELECT * FROM payments"),
        "Expenses":query("SELECT * FROM expenses"),
        "Maintenance":query("SELECT * FROM maintenance"),
        "Stock Adj Batches":query("SELECT * FROM stock_adjustment_batches"),
        "Stock Adj Lines":query("SELECT * FROM stock_adjustment_lines"),
        "Inventory Audit":query("SELECT * FROM inventory_audit_log")
    }
    st.download_button(
        "Download Complete Hotel ERP Report",
        data=excel_file(sheets),
        file_name="Hotel_ERP_Complete_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    st.success("The SQLite database keeps your data after the application closes.")

