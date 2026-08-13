"""
V28 proof script - Reconciliation Run History.
Run directly: python3 PROVE_V28_RUN_HISTORY.py
"""
import sys, importlib.util, pandas as pd, os

os.environ["RETAILRECON_RUN_HISTORY_DB"]="/tmp/prove_run_history.db"
if os.path.exists("/tmp/prove_run_history.db"):
    os.remove("/tmp/prove_run_history.db")

spec=importlib.util.spec_from_file_location("run_history","logic/run_history.py")
run_history=importlib.util.module_from_spec(spec); spec.loader.exec_module(run_history)

ct1={
    "matched": pd.DataFrame([
        {"Unique Transaction ID":"T1","Store Code":"601","Date":pd.Timestamp("2026-08-01"),
         "Payment Type":"MADA","Bank Settled":True,"D365 Amount":100.0},
        {"Unique Transaction ID":"T2","Store Code":"601","Date":pd.Timestamp("2026-08-02"),
         "Payment Type":"VISA","Bank Settled":False,"D365 Amount":200.0},
    ]),
    "unmatched_sales": pd.DataFrame([{"Store Code":"601","Date":pd.Timestamp("2026-08-03")}]),
}
run_id_1=run_history.generate_run_id("20260813")
assert run_id_1=="RUN-20260813-001"
run_history.save_run(run_id_1,ct1,created_at="2026-08-13T10:00:00",
                      username="finance",user_name="Finance Manager",
                      period_from="2026-08-01",period_to="2026-08-02")

run_id_2=run_history.generate_run_id("20260813")
assert run_id_2=="RUN-20260813-002"
ct2={"matched": pd.DataFrame([
    {"Unique Transaction ID":"T3","Store Code":"602","Date":pd.Timestamp("2026-08-05"),
     "Payment Type":"AMEX","Bank Settled":True,"D365 Amount":50.0},
])}
run_history.save_run(run_id_2,ct2,created_at="2026-08-13T11:00:00",
                      username="admin",user_name="System Admin")

runs=run_history.list_runs()
assert len(runs)==2 and set(runs["run_id"])=={run_id_1,run_id_2}

loaded_1=run_history.load_run(run_id_1)
assert len(loaded_1["matched"])==2
assert loaded_1["matched"]["Date"].iloc[0]==pd.Timestamp("2026-08-01")
assert set(loaded_1["matched"]["Unique Transaction ID"])=={"T1","T2"}, \
    "saving Run 2 must never touch Run 1's stored data - the core no-overwrite guarantee"

ct1_v2=dict(ct1); ct1_v2["matched"]=ct1["matched"].copy()
ct1_v2["matched"].loc[ct1_v2["matched"]["Unique Transaction ID"]=="T2","Bank Settled"]=True
run_history.save_run(run_id_1,ct1_v2,created_at="2026-08-13T10:05:00")
assert len(run_history.list_runs())==2, "re-saving the same run_id must update in place, not create a 3rd row"
loaded_1_v2=run_history.load_run(run_id_1)
assert bool(loaded_1_v2["matched"].loc[loaded_1_v2["matched"]["Unique Transaction ID"]=="T2","Bank Settled"].iloc[0]) is True

print("V28 RUN HISTORY PROOF PASS")
