# Hotel ERP – Multi-Level Approval Final

Run `RUN_APP.bat` on Windows or install requirements and run:

```bash
streamlit run app.py
```

Approval tiers:
- Up to SAR 5,000: Manager
- SAR 5,001–25,000: Manager → Accounts
- Above SAR 25,000: Manager → Accounts → Admin

Opening stock remains Manager-only. POS consumption posts immediately. GRN stock posts only after final approval.
