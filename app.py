import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import hmac
import os
from datetime import datetime, date, timedelta
from io import BytesIO
from pathlib import Path

import approvals

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hotel_erp.db"

st.set_page_config(
    page_title="Hotel ERP Commercial Prototype",
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

[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,.96);
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 28px rgba(15,23,42,.06);
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

/* Login screen polish */
.block-container { padding-top: 2rem; padding-bottom: 3rem; }
@media (max-width: 900px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
}
</style>
""", unsafe_allow_html=True)

ALL_MODULES = [
    "Dashboard","Reservations","Front Desk","Rooms","Restaurant POS",
    "Kitchen Display","Kitchen Performance","Housekeeping","Inventory",
    "Purchasing","Maintenance","Payments","Expenses","Finance Reports","Reports",
    "User Access"
]

MODULE_ICONS = {
    "Dashboard": "📊", "Reservations": "🗓️", "Front Desk": "🛎️",
    "Rooms": "🛏️", "Restaurant POS": "🍽️", "Kitchen Display": "👨‍🍳",
    "Kitchen Performance": "⏱️", "Housekeeping": "🧹", "Inventory": "📦",
    "Purchasing": "🛒", "Maintenance": "🛠️", "Payments": "💳",
    "Expenses": "🧾", "Finance Reports": "💹", "Reports": "📑",
    "User Access": "👥"
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

def scalar(sql, params=(), default=0):
    with conn() as c:
        row = c.execute(sql, params).fetchone()
    return default if not row or row[0] is None else row[0]

def next_code(prefix, table):
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

migrate_users()
migrate_inventory_approval()
migrate_user_access()
approvals.init_approval_schema(conn)

# ---------------- Helpers ----------------
def money(v):
    return f"SAR {float(v or 0):,.2f}"

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
        "Accounts": {"Dashboard","Payments","Expenses","Purchasing","Inventory","Finance Reports","Reports"}
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
    st.title("🏨 Hotel ERP Commercial Prototype")
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
st.sidebar.markdown("## 🏨 Hotel ERP")
st.sidebar.markdown(f"**👤 {user['full_name']}**")
st.sidebar.caption(f"Role: {user['role']}")
st.sidebar.divider()

visible_pages = [p for p in ALL_MODULES if page_allowed(user["username"], p, user["role"])]

if not visible_pages:
    st.warning("You currently have no module access. Contact the system administrator.")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    st.stop()

page = st.sidebar.radio("Navigation", visible_pages, format_func=lambda p: f"{MODULE_ICONS.get(p, '•')}  {p}")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()


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
            ["Accounts", "Dashboard, Payments, Expenses, Purchasing, Inventory, Finance Reports, Reports"]
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
    occupancy = occupied / total_rooms * 100 if total_rooms else 0
    room_revenue = scalar("""
        SELECT SUM(
            MAX(julianday(checkout_date)-julianday(checkin_date),1) * room_rate
        ) FROM reservations WHERE status IN ('Checked-in','Checked-out')
    """)
    restaurant_sales = scalar("SELECT SUM(amount) FROM orders")
    collections = scalar("SELECT SUM(amount) FROM payments")
    expenses = scalar("SELECT SUM(amount) FROM expenses")
    open_kot = scalar("SELECT COUNT(*) FROM orders WHERE status NOT IN ('Served','Cancelled')")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Occupancy", f"{occupancy:.1f}%")
    c2.metric("Room Revenue", money(room_revenue))
    c3.metric("Restaurant Sales", money(restaurant_sales))
    c4.metric("Open KOT", int(open_kot))
    c5.metric("Net Cash", money(collections-expenses))

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Room Status")
        room_status = query("SELECT status, COUNT(*) rooms FROM rooms GROUP BY status")
        st.bar_chart(room_status.set_index("status"))
        st.dataframe(query("SELECT room_no, room_type, status, housekeeping FROM rooms"), use_container_width=True, hide_index=True)
    with c2:
        st.subheader("Stock Alerts")
        stocks = stock_df()
        alerts = stocks[stocks["stock_status"]=="REORDER"]
        if alerts.empty:
            st.success("No stock items below reorder level.")
        else:
            st.dataframe(alerts[["item_code","item_name","available_qty","reorder_level","unit"]], use_container_width=True, hide_index=True)
        st.subheader("Operational Alerts")
        open_maintenance = scalar("SELECT COUNT(*) FROM maintenance WHERE status!='Closed'")
        delayed_kitchen = scalar("SELECT COUNT(*) FROM orders WHERE status IN ('New','Preparing') AND (julianday('now')-julianday(order_time))*1440 > target_minutes")
        st.write(f"Open maintenance tickets: **{open_maintenance}**")
        st.write(f"Delayed kitchen orders: **{delayed_kitchen}**")

# ---------------- Reservations ----------------
elif page == "Reservations":
    st.title("Reservations")
    available = query("SELECT room_no, room_type, rate FROM rooms WHERE status='Available'")
    with st.form("reservation"):
        c1,c2,c3 = st.columns(3)
        guest = c1.text_input("Guest Name")
        mobile = c2.text_input("Mobile")
        id_no = c3.text_input("Passport / ID")
        c1,c2,c3 = st.columns(3)
        room = c1.selectbox("Room", available["room_no"].tolist() if not available.empty else ["No room"])
        checkin = c2.date_input("Check-in", date.today())
        checkout = c3.date_input("Check-out", date.today()+timedelta(days=1))
        c1,c2,c3,c4 = st.columns(4)
        adults = c1.number_input("Adults",1,10,1)
        children = c2.number_input("Children",0,10,0)
        default_rate = float(available.loc[available["room_no"]==room,"rate"].iloc[0]) if not available.empty else 0.0
        rate = c3.number_input("Nightly Rate",0.0,value=default_rate)
        deposit = c4.number_input("Deposit",0.0,value=0.0)
        source = st.selectbox("Booking Source",["Walk-in","Direct","Website","Corporate","Travel Agent"])
        save = st.form_submit_button("Create Reservation", type="primary")
    if save:
        if not guest.strip() or room=="No room" or checkout<=checkin:
            st.error("Enter valid guest, room and dates.")
        else:
            rid = next_code("RSV","reservations")
            execute("""INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (rid,guest,mobile,id_no,room,str(checkin),str(checkout),adults,children,
                     "Reserved",rate,deposit,source,datetime.now().isoformat(timespec="seconds")))
            execute("UPDATE rooms SET status='Reserved' WHERE room_no=?",(room,))
            st.success(f"Reservation {rid} created.")
            st.rerun()
    st.dataframe(query("SELECT * FROM reservations ORDER BY created_at DESC"), use_container_width=True, hide_index=True)

# ---------------- Front Desk ----------------
elif page == "Front Desk":
    st.title("Front Desk")
    t1,t2,t3 = st.tabs(["Check-in","Room Transfer","Check-out"])
    with t1:
        df=query("SELECT * FROM reservations WHERE status='Reserved'")
        if df.empty: st.info("No pending arrivals.")
        else:
            rid=st.selectbox("Reservation",df["reservation_id"].tolist())
            if st.button("Check-in Guest",type="primary"):
                room=str(df.loc[df["reservation_id"]==rid,"room_no"].iloc[0])
                execute("UPDATE reservations SET status='Checked-in' WHERE reservation_id=?",(rid,))
                execute("UPDATE rooms SET status='Occupied' WHERE room_no=?",(room,))
                st.success("Guest checked in."); st.rerun()
    with t2:
        df=query("SELECT * FROM reservations WHERE status='Checked-in'")
        available=query("SELECT room_no FROM rooms WHERE status='Available'")
        if df.empty or available.empty: st.info("Checked-in guest and available room are required.")
        else:
            rid=st.selectbox("Guest Reservation",df["reservation_id"].tolist(),key="tr_rid")
            new_room=st.selectbox("New Room",available["room_no"].tolist())
            if st.button("Transfer Room"):
                old_room=str(df.loc[df["reservation_id"]==rid,"room_no"].iloc[0])
                execute("UPDATE reservations SET room_no=? WHERE reservation_id=?",(new_room,rid))
                execute("UPDATE rooms SET status='Available', housekeeping='Dirty' WHERE room_no=?",(old_room,))
                execute("UPDATE rooms SET status='Occupied' WHERE room_no=?",(new_room,))
                st.success(f"Transferred from {old_room} to {new_room}."); st.rerun()
    with t3:
        df=query("SELECT * FROM reservations WHERE status='Checked-in'")
        if df.empty: st.info("No checked-in guests.")
        else:
            rid=st.selectbox("Reservation",df["reservation_id"].tolist(),key="co_rid")
            row=df[df["reservation_id"]==rid].iloc[0]
            nights=max((pd.to_datetime(row["checkout_date"])-pd.to_datetime(row["checkin_date"])).days,1)
            room_charge=nights*float(row["room_rate"])
            food=scalar("SELECT SUM(amount) FROM orders WHERE order_type='Room Service' AND table_room=?",(str(row["room_no"]),))
            balance=room_charge+food-float(row["deposit"])
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Room",money(room_charge)); c2.metric("Food",money(food))
            c3.metric("Deposit",money(row["deposit"])); c4.metric("Balance",money(balance))
            method=st.selectbox("Payment Method",["Cash","MADA","Visa","MasterCard","Bank Transfer"])
            if st.button("Complete Checkout",type="primary"):
                pid=next_code("PAY","payments")
                execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?)",
                        (pid,datetime.now().isoformat(timespec="seconds"),rid,row["guest_name"],method,balance,"Hotel Checkout"))
                execute("UPDATE reservations SET status='Checked-out' WHERE reservation_id=?",(rid,))
                execute("UPDATE rooms SET status='Available', housekeeping='Dirty' WHERE room_no=?",(str(row["room_no"]),))
                st.success("Checkout completed."); st.rerun()

# ---------------- Rooms ----------------
elif page == "Rooms":
    st.title("Room Management")
    st.dataframe(query("SELECT * FROM rooms"),use_container_width=True,hide_index=True)

# ---------------- Restaurant POS ----------------
elif page == "Restaurant POS":
    st.title("Restaurant POS")
    menu=query("SELECT * FROM menu")
    checked=query("""
        SELECT room_no, guest_name
        FROM reservations
        WHERE status='Checked-in'
        ORDER BY CAST(room_no AS INTEGER)
    """)

    if "pos_cart" not in st.session_state:
        st.session_state.pos_cart=[]

    # Order header
    order_type=st.selectbox(
        "Order Type",
        ["Dine-in","Takeaway","Room Service"],
        key="pos_order_type"
    )

    c1,c2=st.columns(2)
    if order_type=="Room Service":
        if checked.empty:
            location=c1.selectbox("Room No",["No checked-in rooms"])
            guest=c2.text_input("Guest Name",value="",disabled=True)
        else:
            room_options=checked["room_no"].astype(str).tolist()
            location=c1.selectbox("Room No",room_options)
            guest_name=checked.loc[
                checked["room_no"].astype(str)==str(location),"guest_name"
            ].iloc[0]
            guest=c2.text_input("Guest Name",value=str(guest_name),disabled=True)
    elif order_type=="Dine-in":
        location=c1.text_input("Table No",value="T01")
        guest=c2.text_input("Guest / Reference",value="Walk-in")
    else:
        location=c1.text_input("Takeaway Reference",value="Takeaway")
        guest=c2.text_input("Customer Name",value="Walk-in")

    st.subheader("Add Menu Items")
    with st.form("add_pos_item", clear_on_submit=False):
        c1,c2,c3=st.columns(3)
        item=c1.selectbox("Menu Item",menu["item_name"].tolist())
        m=menu[menu["item_name"]==item].iloc[0]
        qty=c2.number_input("Qty",1,50,1)
        rate=c3.number_input("Rate",0.0,value=float(m["price"]),key=f"rate_{m['item_code']}")
        c1,c2,c3=st.columns(3)
        priority=c1.selectbox("Priority",["Normal","High","VIP"])
        chef=c2.selectbox("Chef",["Unassigned","Chef Ahmed","Chef Kumar","Chef Maria"])
        instructions=c3.text_input("Instructions")
        add_item=st.form_submit_button("Add Item to Order",type="primary")

    if add_item:
        st.session_state.pos_cart.append({
            "item_code":str(m["item_code"]),
            "item_name":str(m["item_name"]),
            "qty":float(qty),
            "rate":float(rate),
            "amount":float(qty)*float(rate),
            "station":str(m["station"]),
            "chef":chef,
            "priority":priority,
            "instructions":instructions,
            "target_minutes":int(m["target_minutes"]),
            "ingredient":str(m["ingredient"] or ""),
            "qty_per_item":float(m["qty_per_item"] or 0)
        })
        st.success(f"{item} added to the order.")
        st.rerun()

    st.subheader("Current Order")
    if not st.session_state.pos_cart:
        st.info("Add one or more menu items before sending the order to the kitchen.")
    else:
        cart_df=pd.DataFrame(st.session_state.pos_cart)
        cart_df.insert(0,"Line",range(1,len(cart_df)+1))
        st.dataframe(
            cart_df[["Line","item_name","qty","rate","amount","station","chef","priority","instructions"]],
            use_container_width=True,
            hide_index=True
        )
        c1,c2,c3=st.columns(3)
        c1.metric("Items",len(cart_df))
        c2.metric("Total Quantity",f"{cart_df['qty'].sum():g}")
        c3.metric("Order Total",money(cart_df["amount"].sum()))

        remove_line=st.selectbox("Remove Item Line",cart_df["Line"].tolist())
        b1,b2,b3=st.columns(3)
        if b1.button("Remove Selected Item"):
            st.session_state.pos_cart.pop(int(remove_line)-1)
            st.rerun()
        if b2.button("Clear Order"):
            st.session_state.pos_cart=[]
            st.rerun()
        send=b3.button("Send Complete Order to Kitchen",type="primary")

        if send:
            if order_type=="Room Service" and location=="No checked-in rooms":
                st.error("No checked-in room is available.")
            else:
                kot=next_code("KOT","orders")
                order_time=datetime.now().isoformat(timespec="seconds")
                payment_status="Room Charge" if order_type=="Room Service" else "Pending"
                for line in st.session_state.pos_cart:
                    oid=next_code("ORD","orders")
                    execute("""INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (oid,kot,order_time,order_type,str(location),guest,
                             line["item_code"],line["item_name"],line["qty"],line["rate"],line["amount"],
                             line["station"],line["chef"],line["priority"],line["instructions"],
                             line["target_minutes"],"","","","New",payment_status))
                    if line["ingredient"] and line["qty_per_item"]>0:
                        execute("UPDATE inventory SET issued_qty=issued_qty+? WHERE item_name=?",
                                (line["qty"]*line["qty_per_item"],line["ingredient"]))
                item_count=len(st.session_state.pos_cart)
                st.session_state.pos_cart=[]
                st.success(f"{kot} sent to the kitchen with {item_count} items.")
                st.rerun()

    st.subheader("Order History")
    st.dataframe(query("SELECT * FROM orders ORDER BY order_time DESC, kot_no DESC"),use_container_width=True,hide_index=True)

    unpaid=query("SELECT * FROM orders WHERE payment_status='Pending'")
    if not unpaid.empty:
        kot_options=unpaid["kot_no"].drop_duplicates().tolist()
        selected_kots=st.multiselect("KOTs to settle",kot_options)
        method=st.selectbox("Method",["Cash","MADA","Visa","MasterCard"],key="rest_pay")
        if selected_kots:
            settle_df=unpaid[unpaid["kot_no"].isin(selected_kots)]
            due=float(settle_df["amount"].sum())
            st.info(f"Amount due: {money(due)}")
            if st.button("Receive Payment"):
                pid=next_code("PAY","payments")
                execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?)",
                        (pid,datetime.now().isoformat(timespec="seconds"),",".join(selected_kots),
                         "Restaurant",method,due,"Restaurant Sale"))
                for kot_no in selected_kots:
                    execute("UPDATE orders SET payment_status='Paid' WHERE kot_no=?",(kot_no,))
                st.success("Payment received for the selected KOTs.")
                st.rerun()

# ---------------- Kitchen ----------------
elif page == "Kitchen Display":
    st.title("Kitchen Display System")
    df=query("""
        SELECT *,
        CAST((julianday('now')-julianday(order_time))*1440 AS INTEGER) elapsed_minutes
        FROM orders WHERE status NOT IN ('Served','Cancelled')
        ORDER BY CASE priority WHEN 'VIP' THEN 1 WHEN 'High' THEN 2 ELSE 3 END, order_time
    """)
    if df.empty: st.info("No open kitchen orders.")
    else:
        df["delay_status"]=df.apply(lambda r:"Delayed" if r["elapsed_minutes"]>r["target_minutes"] and r["status"] not in ["Ready"] else "On Time",axis=1)
        st.dataframe(df[["kot_no","order_time","order_type","table_room","item_name","qty","station","chef","priority","instructions","elapsed_minutes","target_minutes","delay_status","status"]],use_container_width=True,hide_index=True)
        kot=st.selectbox("KOT",df["kot_no"].tolist())
        status=st.selectbox("New Status",["New","Preparing","Ready","Served","Cancelled"])
        chef=st.selectbox("Chef",["Unassigned","Chef Ahmed","Chef Kumar","Chef Maria"])
        if st.button("Update KOT",type="primary"):
            now=datetime.now().isoformat(timespec="seconds")
            execute("UPDATE orders SET status=?, chef=? WHERE kot_no=?",(status,chef,kot))
            if status=="Preparing": execute("UPDATE orders SET started_at=? WHERE kot_no=?",(now,kot))
            if status=="Ready": execute("UPDATE orders SET ready_at=? WHERE kot_no=?",(now,kot))
            if status=="Served": execute("UPDATE orders SET served_at=? WHERE kot_no=?",(now,kot))
            st.success("KOT updated."); st.rerun()

elif page == "Kitchen Performance":
    st.title("Kitchen Performance")
    df=query("""
        SELECT station, chef, COUNT(*) orders, SUM(amount) sales,
        AVG(CASE WHEN ready_at!='' THEN (julianday(ready_at)-julianday(order_time))*1440 END) avg_prep_minutes
        FROM orders GROUP BY station, chef
    """)
    st.dataframe(df,use_container_width=True,hide_index=True)

# ---------------- Housekeeping ----------------
elif page == "Housekeeping":
    st.title("Housekeeping")
    rooms=query("SELECT * FROM rooms")
    st.dataframe(rooms,use_container_width=True,hide_index=True)
    c1,c2=st.columns(2)
    room=c1.selectbox("Room",rooms["room_no"].tolist())
    status=c2.selectbox("Status",["Clean","Dirty","Cleaning","Inspected","Out of Service"])
    if st.button("Update Room"):
        execute("UPDATE rooms SET housekeeping=? WHERE room_no=?",(status,room))
        if status=="Out of Service": execute("UPDATE rooms SET status='Out of Service' WHERE room_no=?",(room,))
        elif status=="Clean" and scalar("SELECT COUNT(*) FROM reservations WHERE room_no=? AND status='Checked-in'",(room,))==0:
            execute("UPDATE rooms SET status='Available' WHERE room_no=?",(room,))
        st.success("Room updated."); st.rerun()

# ---------------- Inventory ----------------
elif page == "Inventory":
    st.title("Inventory Control Center")
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
        category_filter = st.multiselect(
            "Filter Category",
            sorted(stocks["category"].dropna().unique().tolist()),
            default=sorted(stocks["category"].dropna().unique().tolist())
        )
        filtered_stocks = stocks[stocks["category"].isin(category_filter)] if category_filter else stocks
        st.dataframe(filtered_stocks, use_container_width=True, hide_index=True)

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
    st.title("Purchasing, GRN & Invoice Booking")

    def required_approval(total_value):
        if total_value <= 5000:
            return "Manager"
        elif total_value <= 20000:
            return "Accounts"
        return "Admin"

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Suppliers",
        "Create Purchase Order",
        "Approval Queue",
        "Goods Receipt (GRN)",
        "Invoice Booking",
        "Invoice Payments",
        "Cancel PO"
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

# ---------------- Finance ----------------
elif page == "Finance Reports":
    st.title("Finance Reports")
    room_rev=scalar("""SELECT SUM(MAX(julianday(checkout_date)-julianday(checkin_date),1)*room_rate)
                       FROM reservations WHERE status IN ('Checked-in','Checked-out')""")
    rest_rev=scalar("SELECT SUM(amount) FROM orders")
    vat_output=(room_rev+rest_rev)*15/115
    purchases=scalar("SELECT SUM(total) FROM purchase_orders")
    expenses=scalar("SELECT SUM(amount) FROM expenses")
    gross_profit=room_rev+rest_rev-purchases-expenses
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Total Revenue",money(room_rev+rest_rev))
    c2.metric("Output VAT",money(vat_output))
    c3.metric("Purchases & Expenses",money(purchases+expenses))
    c4.metric("Estimated Profit",money(gross_profit))
    pnl=pd.DataFrame([
        ["Room Revenue",room_rev],
        ["Restaurant Revenue",rest_rev],
        ["Total Revenue",room_rev+rest_rev],
        ["Purchases",purchases],
        ["Operating Expenses",expenses],
        ["Estimated Profit",gross_profit]
    ],columns=["Line","Amount"])
    st.dataframe(pnl,use_container_width=True,hide_index=True)

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

