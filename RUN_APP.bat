@echo off
cd /d "%~dp0"
echo Starting Hotel ERP Inventory Approval and LP Audit...
python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
