
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta
from io import BytesIO

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hotel_erp.db"

st.set_page_config(
    page_title="Hotel ERP Enterprise",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Helpers
# ============================================================
def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def query(sql, params=()):
    try:
        with conn() as c:
            return pd.read_sql_query(sql, c, params=params)
    except Exception:
        return pd.DataFrame()

def execute(sql, params=()):
    with conn() as c:
        c.execute(sql, params)
        c.commit()

def scalar(sql, params=(), default=0):
    try:
        with conn() as c:
            row = c.execute(sql, params).fetchone()
        return default if not row or row[0] is None else row[0]
    except Exception:
        return default

def money(v):
    return f"{float(v or 0):,.2f}"

def next_code(prefix, table):
    count = int(scalar(f"SELECT COUNT(*) FROM {table}", default=0)) + 1
    return f"{prefix}{date.today().strftime('%y%m%d')}{count:04d}"

def excel_bytes(df, sheet_name="Data"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()

def rerun_to(page_name):
    st.session_state["page"] = page_name
    st.rerun()

# ============================================================
# Session
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "Reservations"

if "reservation_page_no" not in st.session_state:
    st.session_state.reservation_page_no = 1

# ============================================================
# Enterprise CSS
# ============================================================
st.markdown("""
<style>
:root{
  --navy:#071a33;
  --navy2:#0b2f5b;
  --blue:#2563eb;
  --blue2:#1d4ed8;
  --bg:#f4f7fb;
  --card:#ffffff;
  --text:#0f172a;
  --muted:#64748b;
  --line:#dce4ef;
  --green:#16a34a;
  --orange:#f97316;
  --purple:#7c3aed;
  --cyan:#0891b2;
  --red:#dc2626;
}

html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
.block-container { max-width: 1800px; padding: 0 1.6rem 2.5rem 1.6rem; }
[data-testid="stHeader"] { background: rgba(255,255,255,.95); border-bottom:1px solid var(--line); }
[data-testid="stToolbar"] { top:.45rem; }

[data-testid="stSidebar"]{
  background:linear-gradient(180deg,var(--navy) 0%,#08284e 68%,#0a3662 100%);
  border-right:1px solid rgba(255,255,255,.08);
  min-width:220px !important;
  width:220px !important;
}
[data-testid="stSidebar"] > div:first-child { padding:0 !important; }
[data-testid="stSidebar"] * { color:#eef6ff !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { margin:0; }

.erp-brand{
  padding:1.15rem 1.1rem 1rem;
  border-bottom:1px solid rgba(255,255,255,.08);
}
.erp-brand-title{font-size:1.28rem;font-weight:900;display:flex;align-items:center;gap:.6rem;}
.erp-brand-sub{font-size:.7rem;color:#b8c7da !important;margin-top:.15rem;}
.nav-group{font-size:.63rem;font-weight:900;letter-spacing:.1em;color:#9fb4ce !important;padding:.95rem 1rem .35rem;}
.nav-item{
  display:block;padding:.58rem .8rem;margin:.1rem .55rem;border-radius:8px;
  color:#e6eef8 !important;text-decoration:none;font-size:.79rem;font-weight:650;
}
.nav-item.active{background:linear-gradient(90deg,#2458b8,#1e63ca);box-shadow:0 8px 18px rgba(0,0,0,.18);}
.nav-item:hover{background:rgba(255,255,255,.08);}
.sidebar-footer{padding:1rem;border-top:1px solid rgba(255,255,255,.08);font-size:.68rem;color:#9fb4ce !important;}

.topbar{
  height:56px;background:white;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
  margin:0 -1.6rem 1rem;padding:0 1.6rem;position:sticky;top:0;z-index:20;
}
.top-left{display:flex;align-items:center;gap:1rem;}
.menu-icon{font-size:1.2rem;color:#1e293b;}
.search-box{
  width:360px;height:36px;border:1px solid var(--line);border-radius:8px;
  display:flex;align-items:center;padding:0 .8rem;color:#94a3b8;font-size:.78rem;background:#fff;
}
.top-right{display:flex;align-items:center;gap:1rem;color:#334155;font-size:.78rem;}
.icon-circle{width:32px;height:32px;border-radius:50%;background:#eef2f7;display:flex;align-items:center;justify-content:center;}
.admin-meta{line-height:1.2}.admin-name{font-weight:800;color:#0f172a}.admin-role{font-size:.66rem;color:#64748b}

.page-head{display:flex;justify-content:space-between;align-items:flex-start;margin:0 0 1rem;}
.page-title{font-size:1.55rem;font-weight:900;color:#0f172a;letter-spacing:-.025em;}
.breadcrumb{font-size:.72rem;color:#64748b;margin-top:.35rem;}
.primary-btn{
  background:linear-gradient(90deg,var(--blue),var(--blue2));color:white;border-radius:8px;
  padding:.72rem 1rem;font-weight:800;font-size:.78rem;box-shadow:0 8px 18px rgba(37,99,235,.22);
}

.kpi-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.75rem;margin-bottom:.85rem;}
.kpi-card{
  background:white;border:1px solid var(--line);border-radius:10px;padding:.78rem .9rem;
  box-shadow:0 4px 14px rgba(15,23,42,.05);display:flex;justify-content:space-between;align-items:center;
}
.kpi-label{font-size:.68rem;color:#475569;font-weight:800;}
.kpi-value{font-size:1.38rem;font-weight:900;color:#0f172a;margin-top:.18rem;}
.kpi-sub{font-size:.64rem;color:#64748b;margin-top:.1rem;}
.kpi-icon{width:42px;height:42px;border-radius:13px;display:flex;align-items:center;justify-content:center;font-size:1.35rem;}
.i-blue{background:#eaf1ff;color:#2563eb}.i-green{background:#e8f8ef;color:#16a34a}
.i-orange{background:#fff1e8;color:#f97316}.i-purple{background:#f0e9ff;color:#7c3aed}.i-cyan{background:#e5f8fb;color:#0891b2}

.panel{
  background:white;border:1px solid var(--line);border-radius:10px;
  box-shadow:0 5px 16px rgba(15,23,42,.05);padding:.8rem .9rem;margin-bottom:.85rem;
}
.panel-title{font-size:.85rem;font-weight:900;color:#0f172a;margin-bottom:.7rem;}
.filter-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.65rem;}

[data-baseweb="input"] > div, [data-baseweb="select"] > div {
  min-height:38px !important;background:white !important;border:1px solid var(--line) !important;border-radius:7px !important;
}
.stTextInput label,.stSelectbox label,.stDateInput label,.stNumberInput label{font-size:.68rem!important;font-weight:800!important;color:#334155!important;}
.stButton > button,.stDownloadButton > button{
  border-radius:7px!important;min-height:38px!important;font-size:.74rem!important;font-weight:800!important;
}
.stButton > button[kind="primary"]{background:linear-gradient(90deg,var(--blue),var(--blue2))!important;border:0!important;color:white!important;}

[data-testid="stDataFrame"]{
  border:1px solid var(--line);border-radius:8px;overflow:hidden;background:white;
}
.res-table-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.6rem;}
.res-count{font-size:.88rem;font-weight:900;color:#0f172a;}
.table-tools{font-size:.7rem;color:#475569;display:flex;gap:.7rem;}
.status-pill{padding:.2rem .45rem;border-radius:6px;font-size:.62rem;font-weight:800;}
.footer-kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:0;background:white;border:1px solid var(--line);border-radius:10px;overflow:hidden;}
.footer-kpi{padding:.75rem .9rem;border-right:1px solid var(--line);display:flex;gap:.65rem;align-items:center;}
.footer-kpi:last-child{border-right:0}.footer-icon{font-size:1.3rem}.footer-label{font-size:.64rem;color:#475569;font-weight:800}.footer-value{font-size:1.05rem;font-weight:900;color:#0f172a}

@media (max-width:1200px){
  .kpi-grid{grid-template-columns:repeat(3,1fr)}
  .filter-grid{grid-template-columns:repeat(3,1fr)}
  .footer-kpis{grid-template-columns:repeat(3,1fr)}
}
@media (max-width:800px){
  [data-testid="stSidebar"]{min-width:200px!important;width:200px!important}
  .search-box{width:220px}
  .kpi-grid,.filter-grid,.footer-kpis{grid-template-columns:1fr}
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("""
    <div class="erp-brand">
      <div class="erp-brand-title">🏨 <span>Hotel ERP</span></div>
      <div class="erp-brand-sub">Complete Hotel Management</div>
    </div>
    """, unsafe_allow_html=True)

    nav_sections = {
        "MAIN": [("Dashboard","🏠")],
        "FRONT OFFICE": [
            ("Reservations","🗓️"),("Walk-in","🚶"),("Guests","👥"),
            ("Room Management","🛏️"),("Check-in","🛎️"),("Check-out","⏱️")
        ],
        "POS & F&B": [("Restaurant POS","🍽️"),("Kitchen Display","👨‍🍳"),("Bar POS","🍷")],
        "HOUSEKEEPING": [("Housekeeping","🧹"),("Lost & Found","🧳"),("Maintenance","🛠️")],
        "INVENTORY": [("Inventory","📦"),("Stock Adjustments","🧾"),("Stock Take","📋")],
        "PURCHASING": [("PR / Indent","📝"),("Purchase Orders","🛒"),("GRN","📥")],
        "FINANCE": [("Supplier Invoices","📄"),("Payments","💳"),("Reports","📊")]
    }

    for section, items in nav_sections.items():
        st.markdown(f'<div class="nav-group">{section}</div>', unsafe_allow_html=True)
        for label, icon in items:
            active = " active" if st.session_state.page == label else ""
            if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                rerun_to(label)

    st.markdown('<div class="sidebar-footer">© 2026 Hotel ERP<br>Version 1.0 Demo</div>', unsafe_allow_html=True)

# ============================================================
# Topbar
# ============================================================
st.markdown("""
<div class="topbar">
  <div class="top-left">
    <div class="menu-icon">☰</div>
    <div class="search-box">⌕ &nbsp; Search guest, booking, room, invoice...</div>
  </div>
  <div class="top-right">
    <div>📅</div><div>🔔 <span style="color:#dc2626;font-weight:900">12</span></div>
    <div class="icon-circle">👤</div>
    <div class="admin-meta"><div class="admin-name">Admin</div><div class="admin-role">System Administrator</div></div>
    <div>⌄</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Reservations page
# ============================================================
def reservations_page():
    reservations = query("SELECT * FROM reservations ORDER BY created_at DESC")
    rooms = query("SELECT * FROM rooms ORDER BY room_no")

    today = str(date.today())
    total_res = len(reservations)
    today_checkin = int((reservations["checkin_date"] == today).sum()) if not reservations.empty else 0
    today_checkout = int((reservations["checkout_date"] == today).sum()) if not reservations.empty else 0
    inhouse = int((reservations["status"] == "Checked-in").sum()) if not reservations.empty else 0
    total_rooms = len(rooms)
    occupied = int((rooms["status"] == "Occupied").sum()) if not rooms.empty else 0
    occupancy = occupied / total_rooms * 100 if total_rooms else 0.0

    st.markdown("""
    <div class="page-head">
      <div>
        <div class="page-title">Reservations</div>
        <div class="breadcrumb">Home &nbsp;›&nbsp; Reservations &nbsp;›&nbsp; Reservation List</div>
      </div>
      <div class="primary-btn">＋ New Reservation</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div><div class="kpi-label">Total Reservations</div><div class="kpi-value">{total_res}</div><div class="kpi-sub">Selected period</div></div><div class="kpi-icon i-blue">🗓️</div></div>
      <div class="kpi-card"><div><div class="kpi-label">Today's Check-in</div><div class="kpi-value">{today_checkin}</div><div class="kpi-sub">Today</div></div><div class="kpi-icon i-green">🧳</div></div>
      <div class="kpi-card"><div><div class="kpi-label">Today's Check-out</div><div class="kpi-value">{today_checkout}</div><div class="kpi-sub">Today</div></div><div class="kpi-icon i-orange">🚪</div></div>
      <div class="kpi-card"><div><div class="kpi-label">In-House Guests</div><div class="kpi-value">{inhouse}</div><div class="kpi-sub">Currently staying</div></div><div class="kpi-icon i-purple">👥</div></div>
      <div class="kpi-card"><div><div class="kpi-label">Occupancy</div><div class="kpi-value">{occupancy:.2f}%</div><div class="kpi-sub">Today</div></div><div class="kpi-icon i-cyan">◔</div></div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        f1,f2,f3,f4 = st.columns(4)
        guest_search = f1.text_input("Guest Name", placeholder="Search guest name / mobile")
        mobile_search = f2.text_input("Mobile", placeholder="Mobile number")
        id_search = f3.text_input("Passport / ID", placeholder="Passport / ID number")
        room_filter = f4.selectbox("Room", ["All Rooms"] + (rooms["room_no"].astype(str).tolist() if not rooms.empty else []))

        f1,f2,f3,f4,f5,f6 = st.columns([1.2,1.2,.7,.7,1.1,1.1])
        from_date = f1.date_input("Check-in Date", date.today()-timedelta(days=365))
        to_date = f2.date_input("Check-out Date", date.today()+timedelta(days=365))
        adults_filter = f3.selectbox("Adults", ["All",1,2,3,4,5])
        children_filter = f4.selectbox("Children", ["All",0,1,2,3,4])
        source_filter = f5.selectbox("Booking Source", ["All Sources"] + (sorted(reservations["source"].dropna().astype(str).unique().tolist()) if not reservations.empty else []))
        status_filter = f6.selectbox("Status", ["All Status"] + (sorted(reservations["status"].dropna().astype(str).unique().tolist()) if not reservations.empty else []))

        b1,b2,b3,b4 = st.columns([5.5,1,1,1.2])
        with b2:
            search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)
        with b3:
            reset_clicked = st.button("↻ Reset", use_container_width=True)
        with b4:
            export_placeholder = st.empty()

    filtered = reservations.copy()
    if not filtered.empty:
        checkin_dt = pd.to_datetime(filtered["checkin_date"], errors="coerce")
        checkout_dt = pd.to_datetime(filtered["checkout_date"], errors="coerce")
        filtered = filtered[
            (checkin_dt.dt.date >= from_date)
            & (checkout_dt.dt.date <= to_date)
        ]
        if guest_search.strip():
            n = guest_search.strip().lower()
            filtered = filtered[
                filtered["guest_name"].fillna("").astype(str).str.lower().str.contains(n, regex=False)
                | filtered["mobile"].fillna("").astype(str).str.lower().str.contains(n, regex=False)
            ]
        if mobile_search.strip():
            filtered = filtered[filtered["mobile"].fillna("").astype(str).str.contains(mobile_search.strip(), regex=False)]
        if id_search.strip():
            filtered = filtered[filtered["id_number"].fillna("").astype(str).str.contains(id_search.strip(), regex=False)]
        if room_filter != "All Rooms":
            filtered = filtered[filtered["room_no"].astype(str) == str(room_filter)]
        if adults_filter != "All":
            filtered = filtered[pd.to_numeric(filtered["adults"], errors="coerce") == int(adults_filter)]
        if children_filter != "All":
            filtered = filtered[pd.to_numeric(filtered["children"], errors="coerce") == int(children_filter)]
        if source_filter != "All Sources":
            filtered = filtered[filtered["source"] == source_filter]
        if status_filter != "All Status":
            filtered = filtered[filtered["status"] == status_filter]

        ci = pd.to_datetime(filtered["checkin_date"], errors="coerce")
        co = pd.to_datetime(filtered["checkout_date"], errors="coerce")
        filtered["Nights"] = (co-ci).dt.days.clip(lower=0)
        filtered["Room Rate"] = pd.to_numeric(filtered["room_rate"], errors="coerce").fillna(0)
        filtered["Deposit"] = pd.to_numeric(filtered["deposit"], errors="coerce").fillna(0)
        display_cols = [
            "reservation_id","guest_name","mobile","room_no","checkin_date","checkout_date",
            "Nights","adults","children","status","Room Rate","Deposit","source","created_at"
        ]
        display = filtered[display_cols].copy()
        display.columns = [
            "Reservation ID","Guest Name","Mobile","Room No.","Check-in","Check-out",
            "Nights","Adults","Children","Status","Room Rate","Deposit","Source","Created At"
        ]
    else:
        display = pd.DataFrame(columns=[
            "Reservation ID","Guest Name","Mobile","Room No.","Check-in","Check-out",
            "Nights","Adults","Children","Status","Room Rate","Deposit","Source","Created At"
        ])

    export_placeholder.download_button(
        "📗 Export",
        data=excel_bytes(display, "Reservations"),
        file_name=f"Reservation_List_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    with st.container(border=True):
        st.markdown(
            f"""<div class="res-table-head"><div class="res-count">Reservation List ({len(display)})</div>
            <div class="table-tools">▥ Columns &nbsp;&nbsp; ⚲ Filters</div></div>""",
            unsafe_allow_html=True
        )
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=390,
            column_config={
                "Room Rate": st.column_config.NumberColumn(format="%.2f"),
                "Deposit": st.column_config.NumberColumn(format="%.2f"),
            }
        )

    available_rooms = int((rooms["status"]=="Available").sum()) if not rooms.empty else 0
    out_order = int(rooms["status"].isin(["Maintenance","Out of Service"]).sum()) if not rooms.empty else 0
    stayovers = inhouse

    st.markdown(f"""
    <div class="footer-kpis">
      <div class="footer-kpi"><div class="footer-icon">🟢</div><div><div class="footer-label">Today's Arrivals</div><div class="footer-value">{today_checkin}</div></div></div>
      <div class="footer-kpi"><div class="footer-icon">🟠</div><div><div class="footer-label">Today's Departures</div><div class="footer-value">{today_checkout}</div></div></div>
      <div class="footer-kpi"><div class="footer-icon">🛏️</div><div><div class="footer-label">Stayovers</div><div class="footer-value">{stayovers}</div></div></div>
      <div class="footer-kpi"><div class="footer-icon">🏨</div><div><div class="footer-label">Total Rooms</div><div class="footer-value">{total_rooms}</div></div></div>
      <div class="footer-kpi"><div class="footer-icon">🚪</div><div><div class="footer-label">Available Rooms</div><div class="footer-value">{available_rooms}</div></div></div>
      <div class="footer-kpi"><div class="footer-icon">🛠️</div><div><div class="footer-label">Out of Order</div><div class="footer-value">{out_order}</div></div></div>
    </div>
    """, unsafe_allow_html=True)

def placeholder_page(title, icon="📄"):
    st.markdown(f"""
    <div class="page-head">
      <div>
        <div class="page-title">{icon} {title}</div>
        <div class="breadcrumb">Home &nbsp;›&nbsp; {title}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader(f"{title} — Enterprise UI")
        st.info("This module is connected to the new Hotel ERP shell. The full operational workflow can now be migrated from the existing Hotel Control Tower application.")

# ============================================================
# Router
# ============================================================
page = st.session_state.page

if page == "Reservations":
    reservations_page()
elif page == "Dashboard":
    placeholder_page("Dashboard","🏠")
elif page == "Walk-in":
    placeholder_page("Walk-in Reservation","🚶")
elif page == "Guests":
    placeholder_page("Guest Management","👥")
elif page == "Room Management":
    placeholder_page("Room Management","🛏️")
elif page == "Check-in":
    placeholder_page("Check-in","🛎️")
elif page == "Check-out":
    placeholder_page("Check-out","⏱️")
elif page == "Restaurant POS":
    placeholder_page("Restaurant POS","🍽️")
elif page == "Kitchen Display":
    placeholder_page("Kitchen Display","👨‍🍳")
elif page == "Bar POS":
    placeholder_page("Bar POS","🍷")
elif page == "Housekeeping":
    placeholder_page("Housekeeping","🧹")
elif page == "Lost & Found":
    placeholder_page("Lost & Found","🧳")
elif page == "Maintenance":
    placeholder_page("Maintenance","🛠️")
elif page == "Inventory":
    placeholder_page("Inventory","📦")
elif page == "Stock Adjustments":
    placeholder_page("Stock Adjustments","🧾")
elif page == "Stock Take":
    placeholder_page("Stock Take","📋")
elif page == "PR / Indent":
    placeholder_page("Purchase Requisition / Indent","📝")
elif page == "Purchase Orders":
    placeholder_page("Purchase Orders","🛒")
elif page == "GRN":
    placeholder_page("Goods Receipt Note","📥")
elif page == "Supplier Invoices":
    placeholder_page("Supplier Invoices","📄")
elif page == "Payments":
    placeholder_page("Payments","💳")
elif page == "Reports":
    placeholder_page("Reports & Analytics","📊")

st.markdown(
    "<div style='margin-top:1.6rem;padding-top:.8rem;border-top:1px solid #dce4ef;color:#64748b;font-size:.7rem;display:flex;justify-content:space-between'>"
    "<span>© 2026 Hotel ERP. All rights reserved.</span><span>Version 1.0.0</span></div>",
    unsafe_allow_html=True
)
