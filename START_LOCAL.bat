# Hotel ERP Cloud Deployment Guide

## Fastest Test Option: Streamlit Community Cloud

1. Create a GitHub repository named `hotel-erp-demo`.
2. Upload all files from this folder to that repository.
3. Open Streamlit Community Cloud.
4. Select **Create app**.
5. Choose the GitHub repository.
6. Set the main file path to:

```text
app.py
```

7. Deploy the application.
8. Share the generated web link with the client.

### Demo login

```text
Username: admin
Password: admin123
```

## Important SQLite Limitation

This demo uses `hotel_erp.db`.

On many free cloud services, local SQLite data can be lost when the service restarts or redeploys. This is acceptable for a short client demonstration, but not for production.

For a production version, replace SQLite with PostgreSQL or another managed database.

## Render / Railway Deployment

This package includes:

- `Dockerfile`
- `render.yaml`
- `Procfile`
- `.streamlit/config.toml`

Deploy the repository as a Docker web service. The service must expose port 8501 or use the platform-provided `$PORT`.

## Client Test Checklist

Before sharing the link:

1. Login as Admin.
2. Create a reservation.
3. Check in the guest.
4. Create a room-service order.
5. Send multiple items to Kitchen.
6. Create an inventory item.
7. Create a supplier and PO.
8. Approve the PO.
9. Create GRN.
10. Book supplier invoice.
11. Process vendor batch payment.

## Production Requirements

Before live commercial use, add:

- PostgreSQL database
- Encrypted passwords
- Audit trail
- Daily backups
- ZATCA e-invoicing integration
- SSL/domain
- Multi-property controls
- Automated tests
- User activity logging
