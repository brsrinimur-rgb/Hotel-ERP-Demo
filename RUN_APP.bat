
# Hotel ERP Commercial Prototype

A persistent Streamlit hotel ERP prototype with SQLite database.

## Included

- Role-based login
- Reservations and front desk
- Check-in, room transfer and checkout
- Restaurant POS and room service
- Kitchen Display System and KOT workflow
- Automatic ingredient consumption
- Inventory and reorder alerts
- Suppliers and purchase orders
- Housekeeping
- Maintenance tickets
- Payments and expenses
- Finance and VAT summary
- Excel exports
- Persistent SQLite database

## Demo Users

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Manager | manager | manager123 |
| Reception | reception | front123 |
| Restaurant | restaurant | pos123 |
| Kitchen | kitchen | kitchen123 |
| Housekeeping | housekeeping | house123 |
| Accounts | accounts | accounts123 |

## Run on Windows

Extract the folder to:

C:\Hotel_ERP_Commercial_Prototype

Then double-click:

RUN_APP.bat

Or use Command Prompt:

```bat
cd C:\Hotel_ERP_Commercial_Prototype
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Important

The file `hotel_erp.db` is created inside the application folder. Do not delete it if you want to keep entered data.

This is a commercial prototype, not yet a production SaaS. Before selling it as a live hotel system, add encrypted passwords, automated backups, audit logs, ZATCA e-invoicing integration, online booking integrations, tests, and cloud deployment.
