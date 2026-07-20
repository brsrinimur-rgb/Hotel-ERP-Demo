
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from io import BytesIO
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "hotel_erp.db"

st.set_page_config(
    page_title="Hotel ERP Commercial Prototype",
    page_icon="🏨",
    layout="wide"
)

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
        users = [
            ("admin", "admin123", "Admin", "System Administrator"),
            ("manager", "manager123", "Manager", "Hotel Manager"),
            ("reception", "front123", "Reception", "Front Desk"),
            ("restaurant", "pos123", "Restaurant", "Restaurant Cashier"),
            ("kitchen", "kitchen123", "Kitchen", "Kitchen Team"),
            ("housekeeping", "house123", "Housekeeping", "Housekeeping Team"),
            ("accounts", "accounts123", "Accounts", "Accounts Team")
        ]
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

def page_allowed(page, role):
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
    return allowed is None or page in allowed

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
        user = query(
            "SELECT username, role, full_name FROM users WHERE username=? AND password=?",
            (username, password)
        )
        if user.empty:
            st.error("Invalid username or password.")
        else:
            st.session_state.user = user.iloc[0].to_dict()
            st.rerun()

    st.info("Demo admin login: admin / admin123")
    st.stop()

user = st.session_state.user
st.sidebar.title("Hotel ERP")
st.sidebar.write(f"**{user['full_name']}**")
st.sidebar.caption(user["role"])

pages = [
    "Dashboard","Reservations","Front Desk","Rooms","Restaurant POS",
    "Kitchen Display","Kitchen Performance","Housekeeping","Inventory",
    "Purchasing","Maintenance","Payments","Expenses","Finance Reports","Reports"
]
visible_pages = [p for p in pages if page_allowed(p, user["role"])]
page = st.sidebar.radio("Navigation", visible_pages)

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# ---------------- Dashboard ----------------
if page == "Dashboard":
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
    st.title("Inventory & Food Cost")

    tab1, tab2, tab3 = st.tabs(["Inventory List", "Add New Item", "Stock Adjustment"])

    with tab1:
        stocks=stock_df()
        c1,c2,c3=st.columns(3)
        c1.metric("Stock Value",money(stocks["stock_value"].sum()))
        c2.metric("Items to Reorder",int((stocks["stock_status"]=="REORDER").sum()))
        c3.metric("Inventory Items",len(stocks))

        category_filter=st.multiselect(
            "Filter Category",
            sorted(stocks["category"].dropna().unique().tolist()),
            default=sorted(stocks["category"].dropna().unique().tolist())
        )
        filtered_stocks=stocks[stocks["category"].isin(category_filter)] if category_filter else stocks
        st.dataframe(filtered_stocks,use_container_width=True,hide_index=True)

    with tab2:
        st.subheader("Add Inventory Item")
        with st.form("add_inventory_item", clear_on_submit=True):
            c1,c2,c3=st.columns(3)
            item_name=c1.text_input("Item Name")
            category=c2.selectbox(
                "Category",
                ["Food","Beverage","Housekeeping","Maintenance","Linen","Cleaning","Other"]
            )
            unit=c3.selectbox(
                "Unit",
                ["kg","gram","litre","ml","bottle","piece","box","carton","pack","set","roll","dozen"]
            )

            c1,c2,c3=st.columns(3)
            opening_qty=c1.number_input("Opening Quantity",min_value=0.0,value=0.0,step=1.0)
            reorder_level=c2.number_input("Reorder Level",min_value=0.0,value=0.0,step=1.0)
            unit_cost=c3.number_input("Unit Cost (SAR)",min_value=0.0,value=0.0,step=0.50)

            add_item=st.form_submit_button("Add Inventory Item",type="primary")

        if add_item:
            clean_name=item_name.strip()
            if not clean_name:
                st.error("Item name is required.")
            elif scalar("SELECT COUNT(*) FROM inventory WHERE LOWER(item_name)=LOWER(?)",(clean_name,)) > 0:
                st.error("This inventory item already exists.")
            else:
                item_code=next_code("INV","inventory")
                execute(
                    "INSERT INTO inventory VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        item_code,
                        clean_name,
                        category,
                        unit,
                        opening_qty,
                        0.0,
                        0.0,
                        reorder_level,
                        unit_cost
                    )
                )
                st.success(f"{clean_name} added successfully with code {item_code}.")
                st.rerun()

        st.caption("New items will also become available in Purchasing for purchase orders.")

    with tab3:
        st.subheader("Manual Stock Adjustment")
        inventory_items=query("SELECT item_code,item_name,unit FROM inventory ORDER BY item_name")
        if inventory_items.empty:
            st.info("No inventory items available.")
        else:
            with st.form("stock_adjustment"):
                selected_item=st.selectbox(
                    "Inventory Item",
                    inventory_items["item_name"].tolist()
                )
                adjustment_type=st.selectbox(
                    "Adjustment Type",
                    ["Stock Received","Stock Issued / Used"]
                )
                adjustment_qty=st.number_input(
                    "Quantity",
                    min_value=0.01,
                    value=1.0,
                    step=1.0
                )
                update_stock=st.form_submit_button("Update Stock",type="primary")

            if update_stock:
                selected_row=inventory_items[
                    inventory_items["item_name"]==selected_item
                ].iloc[0]

                if adjustment_type=="Stock Received":
                    execute(
                        "UPDATE inventory SET received_qty=received_qty+? WHERE item_code=?",
                        (adjustment_qty,selected_row["item_code"])
                    )
                else:
                    available=scalar(
                        "SELECT opening_qty+received_qty-issued_qty FROM inventory WHERE item_code=?",
                        (selected_row["item_code"],)
                    )
                    if adjustment_qty > float(available):
                        st.error(f"Insufficient stock. Available quantity: {available:.2f}")
                        st.stop()
                    execute(
                        "UPDATE inventory SET issued_qty=issued_qty+? WHERE item_code=?",
                        (adjustment_qty,selected_row["item_code"])
                    )

                st.success(
                    f"{adjustment_type} updated for {selected_item}: "
                    f"{adjustment_qty} {selected_row['unit']}."
                )
                st.rerun()

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
        "PO Payments",
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
                approval_level=required_approval(total)

                st.info(
                    f"Subtotal: {money(subtotal)} | VAT: {money(vat_amount)} | "
                    f"Total: {money(total)} | Required approval: {approval_level}"
                )
                submit=st.form_submit_button("Create & Submit PO",type="primary")

            if submit:
                po=next_code("PO","purchase_orders")
                execute(
                    """INSERT INTO purchase_orders(
                        po_no,po_date,supplier_id,supplier_name,item_code,item_name,
                        qty,unit_cost,vat_rate,total,status,payment_method,
                        payment_terms_days,requested_by,approval_level,approved_by,
                        approved_at,rejection_reason,payment_status,paid_amount,
                        received_at,grn_no,invoice_status
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        po,str(date.today()),supplier_row["supplier_id"],supplier_name,
                        item_row["item_code"],item,qty,unit_cost,vat_rate,total,
                        "Pending Approval",payment_method,payment_terms,user["full_name"],
                        approval_level,"","","","Unpaid",0.0,"","","Not Booked"
                    )
                )
                st.success(f"{po} submitted for {approval_level} approval.")
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
        queue=query("""
            SELECT * FROM purchase_orders
            WHERE status IN ('Pending Approval','Approved','Rejected','Partially Received','Received','Cancelled')
            ORDER BY po_no DESC
        """)

        if queue.empty:
            st.info("No purchase orders available.")
        else:
            role=user["role"]
            approvable=queue[
                (queue["status"]=="Pending Approval") &
                ((queue["approval_level"]==role) | (role=="Admin"))
            ]

            c1,c2,c3,c4=st.columns(4)
            c1.metric("Pending Approval",int((queue["status"]=="Pending Approval").sum()))
            c2.metric("Approved",int((queue["status"]=="Approved").sum()))
            c3.metric("Received",int((queue["status"]=="Received").sum()))
            c4.metric("Rejected",int((queue["status"]=="Rejected").sum()))

            st.dataframe(
                queue[["po_no","supplier_name","item_name","qty","total","status",
                       "approval_level","requested_by","approved_by","grn_no","invoice_status"]],
                use_container_width=True,
                hide_index=True
            )

            if not approvable.empty:
                selected_po=st.selectbox("PO Number",approvable["po_no"].tolist())
                decision=st.radio("Decision",["Approve","Reject"],horizontal=True)
                rejection_reason=st.text_area("Rejection Reason",disabled=(decision=="Approve"))

                if st.button("Submit Decision",type="primary"):
                    if decision=="Reject" and not rejection_reason.strip():
                        st.error("Rejection reason is required.")
                    else:
                        now=datetime.now().isoformat(timespec="seconds")
                        if decision=="Approve":
                            execute(
                                """UPDATE purchase_orders
                                   SET status='Approved',approved_by=?,approved_at=?,rejection_reason=''
                                   WHERE po_no=?""",
                                (user["full_name"],now,selected_po)
                            )
                            st.success(f"{selected_po} approved.")
                        else:
                            execute(
                                """UPDATE purchase_orders
                                   SET status='Rejected',approved_by=?,approved_at=?,rejection_reason=?
                                   WHERE po_no=?""",
                                (user["full_name"],now,rejection_reason.strip(),selected_po)
                            )
                            st.success(f"{selected_po} rejected.")
                        st.rerun()
            else:
                st.info("No purchase orders are awaiting your approval level.")

    with tab4:
        st.subheader("Goods Receipt Note (GRN / GRR)")
        approved=query("""
            SELECT po.*,
                   COALESCE((SELECT SUM(accepted_qty) FROM goods_receipts gr WHERE gr.po_no=po.po_no),0) AS already_received
            FROM purchase_orders po
            WHERE po.status IN ('Approved','Partially Received')
            ORDER BY po.po_no
        """)

        if approved.empty:
            st.info("No approved purchase orders are pending receipt.")
        else:
            po_no=st.selectbox("Approved PO",approved["po_no"].tolist())
            row=approved[approved["po_no"]==po_no].iloc[0]
            outstanding=float(row["qty"])-float(row["already_received"])

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
                create_grn=st.form_submit_button("Create GRN & Update Stock",type="primary")

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
                            remarks,"Posted"
                        )
                    )

                    if accepted_qty > 0:
                        execute(
                            """UPDATE inventory
                               SET received_qty=received_qty+?, unit_cost=?
                               WHERE item_code=?""",
                            (accepted_qty,float(row["unit_cost"]),row["item_code"])
                        )

                    total_received=float(row["already_received"])+accepted_qty
                    new_status="Received" if total_received >= float(row["qty"])-0.0001 else "Partially Received"

                    execute(
                        """UPDATE purchase_orders
                           SET status=?,received_at=?,grn_no=?
                           WHERE po_no=?""",
                        (new_status,datetime.now().isoformat(timespec="seconds"),grn_no,po_no)
                    )

                    st.success(
                        f"{grn_no} posted. Accepted stock {accepted_qty:.2f} "
                        f"added to stock on hand."
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
              AND po.invoice_status!='Booked'
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
            po_no=selected_label.split(" | ")[0]
            row=received_pos[received_pos["po_no"]==po_no].iloc[0]

            # Invoice value is picked from the approved PO.
            po_qty=float(row["qty"] or 0)
            po_unit_cost=float(row["unit_cost"] or 0)
            po_vat_rate=float(row["vat_rate"] or 0)

            subtotal=po_qty*po_unit_cost
            vat_amount=subtotal*po_vat_rate/100
            total_amount=float(row["total"] or (subtotal+vat_amount))

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
                        """INSERT INTO supplier_invoices VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            invoice_id,supplier_invoice_no.strip(),str(invoice_date),
                            po_no,str(row["receipt_grn_no"]),str(row["supplier_name"]),subtotal,
                            vat_amount,total_amount,str(due_date),user["full_name"],
                            datetime.now().isoformat(timespec="seconds"),"Booked"
                        )
                    )
                    execute(
                        "UPDATE purchase_orders SET invoice_status='Booked' WHERE po_no=?",
                        (po_no,)
                    )
                    st.success(f"Invoice {supplier_invoice_no.strip()} booked successfully.")
                    st.rerun()

        st.markdown("### Supplier Invoice Register")
        st.dataframe(
            query("""SELECT invoice_id,invoice_no,invoice_date,po_no,grn_no,
                            supplier_name,subtotal,vat_amount,total_amount,
                            due_date,booked_by,status
                     FROM supplier_invoices ORDER BY booked_at DESC"""),
            use_container_width=True,
            hide_index=True
        )

    with tab6:
        st.subheader("Supplier Payment Processing")

        payable=query("""
            SELECT po.*, si.invoice_no, si.due_date, si.total_amount
            FROM purchase_orders po
            JOIN supplier_invoices si ON si.po_no=po.po_no
            WHERE po.invoice_status='Booked' AND po.payment_status!='Paid'
            ORDER BY po.supplier_name,si.due_date,po.po_no
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
                    "po_no","invoice_no","supplier_name","due_date","total_amount",
                    "payment_method","payment_status","paid_amount","outstanding_amount"
                ]],
                use_container_width=True,
                hide_index=True
            )

            vendor_payable["payment_label"]=vendor_payable.apply(
                lambda r: (
                    f"{r['po_no']} | Inv {r['invoice_no']} | "
                    f"Outstanding {money(r['outstanding_amount'])}"
                ),
                axis=1
            )

            selected_labels=st.multiselect(
                "Select Multiple Invoices / POs for Payment",
                vendor_payable["payment_label"].tolist()
            )

            selected_po_numbers=[
                label.split(" | ")[0]
                for label in selected_labels
            ]

            selected_rows=vendor_payable[
                vendor_payable["po_no"].isin(selected_po_numbers)
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
                "Record Vendor Batch Payment",
                type="primary",
                disabled=(selected_total <= 0)
            ):
                remaining=float(payment_amount)
                paid_items=[]

                allocation_rows=selected_rows.sort_values(
                    ["due_date","po_no"]
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

                    execute(
                        """UPDATE purchase_orders
                           SET paid_amount=?,payment_status=?,payment_method=?
                           WHERE po_no=?""",
                        (
                            new_paid,
                            new_status,
                            payment_method,
                            inv_row["po_no"]
                        )
                    )

                    paid_items.append(
                        f"{inv_row['po_no']}:{allocated:.2f}"
                    )
                    remaining-=allocated

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
                        "Vendor Batch Payment"
                    )
                )

                st.success(
                    f"Batch payment of {money(payment_amount)} recorded for "
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
                invoice_booked=str(row["invoice_status"] or "")=="Booked"
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
        "Payments":query("SELECT * FROM payments"),
        "Expenses":query("SELECT * FROM expenses"),
        "Maintenance":query("SELECT * FROM maintenance")
    }
    st.download_button(
        "Download Complete Hotel ERP Report",
        data=excel_file(sheets),
        file_name="Hotel_ERP_Complete_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    st.success("The SQLite database keeps your data after the application closes.")
