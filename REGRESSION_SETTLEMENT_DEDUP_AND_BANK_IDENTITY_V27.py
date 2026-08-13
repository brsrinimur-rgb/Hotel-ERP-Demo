"""
V27 regression — Settlement Input De-duplication & Bank Row Identity Hardening.

Covers the three narrow V27 fixes:
  1. A file recognized by BOTH filename-based provider detection and
     column-shape settlement-source detection is normalized exactly once.
  2. Bank-credit identity is fully deterministic (Source File + Source Sheet +
     Source Row + Bank Date + Bank Amount) - narration text is never the
     primary key, and two credits with identical narration no longer create
     a double-count / mis-reservation window.
  3. The legacy bank-parser path (core.normalize_bank) stamps Bank Source Row
     and Bank Source Sheet on every row, so non-ANB/non-Al-Rajhi statement
     formats no longer collapse to a single shared identity.

Static checks run against the actual page source (this bug class is page-level
control flow, not a pure function, so it is verified the same way
REGRESSION_MAIN_POS_PAGE_WIRING_V26.py verifies the bank_ext wiring: AST/text
presence, not full page execution). Everything else below actually executes
the real core.py / bank_settlement_extension.py functions.
"""
from pathlib import Path
import ast
import sys
import importlib.util
import pandas as pd

root=Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 1. Static check: the main page must classify by settlement-source shape
#    BEFORE transaction classification, and skip transaction classification
#    for any sheet recognized as a payout file.
# ---------------------------------------------------------------------------
page=root/"pages"/"1_POS_Reconciliation.py"
src=page.read_text(encoding="utf-8")
ast.parse(src)  # must still be valid Python

assert "classify_settlement_source" in src
assert "payout_sheets" in src
# The dedup guard must sit inside the primary upload loop, before core.classify(),
# and must `continue` so the sheet never also reaches normalize_pos()/normalize_tender().
guard_idx=src.index("classify_settlement_source(f.name,df)")
classify_idx=src.index('core.classify(f"{f.name}-{sheet}",df)')
continue_idx=src.index("continue",guard_idx)
assert guard_idx<continue_idx<classify_idx, \
    "settlement-source guard must run, and continue, before transaction classify()"

# ---------------------------------------------------------------------------
# Load the real modules for functional checks.
# ---------------------------------------------------------------------------
spec=importlib.util.spec_from_file_location("core_v27",root/"core.py")
core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

spec2=importlib.util.spec_from_file_location("bank_ext_v27",root/"logic"/"bank_settlement_extension.py")
bank_ext=importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(bank_ext)

# ---------------------------------------------------------------------------
# 2. Functional: a filename that trips provider_signature() ("tap" in name)
#    but whose columns are a genuine TAP payout export must be recognized by
#    classify_settlement_source() - this is exactly the overlap the V27 guard
#    is closing.
# ---------------------------------------------------------------------------
tap_payout_cols=pd.DataFrame([{
    "payout_id":"PO-1","settlement_id":"SET-20260801-1","amount":427.0,
    "status":"paid","payout_date":"2026-08-05","settlement_date":"2026-08-01",
}])
assert core.provider_signature("TAP_Payout_Aug2026.xlsx",tap_payout_cols)=="TAP", \
    "filename-based detection must still fire (confirms the overlap this guard exists for)"
assert core.classify_settlement_source("TAP_Payout_Aug2026.xlsx",tap_payout_cols)=="TAP_PAYOUT", \
    "column-shape detection must also fire on the same file"

# ---------------------------------------------------------------------------
# 3. Functional: legacy bank parser stamps deterministic per-row identity.
# ---------------------------------------------------------------------------
legacy_df=pd.DataFrame([
    {"Date":"2026-08-01","Amount":100.0,"Description":"SAME NARRATION"},
    {"Date":"2026-08-01","Amount":200.0,"Description":"SAME NARRATION"},
    {"Date":"2026-08-02","Amount":0.0,"Description":"SAME NARRATION"},  # zero row must still be dropped
])
out=core.normalize_bank(legacy_df,"TEST BANK",source_file="statement.csv",source_sheet="Sheet1")
assert len(out)==2
assert list(out["Bank Source Row"])==[1,2], "row numbers must reflect original position, not post-filter position"
keys=[bank_ext._bank_row_key(r) for _,r in out.iterrows()]
assert len(set(keys))==2, "two legacy rows with identical narration must still get distinct keys"

# Pre-V27 behavior would have collapsed both rows to the same "LEGACY::<hash>"
# key whenever Bank Source Row was absent. Confirm the key format is the new
# deterministic scheme, not a hash.
assert not any(k.startswith("LEGACY::") for k in keys)
assert "SAME NARRATION" not in "".join(keys), "narration text must never be part of the identity key"

# ---------------------------------------------------------------------------
# 4. Functional: two ANB credits sharing identical narration no longer create
#    a reserve-loop double-count / mis-reservation window (the residual gap
#    called out in the V26 review).
# ---------------------------------------------------------------------------
batches=pd.DataFrame([
    {"Store Code":"601","Terminal ID":"T1","Payment Type":"MADA","Settlement Date":pd.Timestamp("2026-08-01"),
     "Expected Bank Amount":100.0,"Gross Amount":100.0,"Provider":"ANB POS","Transaction Count":1},
    {"Store Code":"601","Terminal ID":"T1","Payment Type":"MADA","Settlement Date":pd.Timestamp("2026-08-01"),
     "Expected Bank Amount":200.0,"Gross Amount":200.0,"Provider":"ANB POS","Transaction Count":1},
])
same_narration="301128607335_55610715_010826 | MADA_0_0_TX_1"
bank_rows=pd.DataFrame([
    {"Bank":"ANB","Bank Date":pd.Timestamp("2026-08-01"),"Bank Amount":amt,"Credit":amt,"Debit":0.0,
     "Bank Source File":"anb.xlsx","Bank Source Sheet":"Sheet1","Bank Source Row":i+1,
     "Description":same_narration,"Provider":"ANB POS",
     "Narration Scheme":"MADA","Narration Terminal ID":"T1","Narration Merchant ID":"301128607335",
     "Narration Source Date":pd.Timestamp("2026-08-01"),"Narration Transaction Count":1,
     "Narration Fee":0.0,"Narration VAT":0.0}
    for i,amt in enumerate([100.0,200.0])
])
result,unmatched=bank_ext.reconcile_card_batches_advanced(batches,bank_rows,tolerance=1.0)
assert (result["Settlement Status"]=="BANK RECEIVED").sum()==2, "both batches must settle independently"
assert set(result["Actual Bank Amount"])=={100.0,200.0}, "each batch must tie to its own distinct bank credit"
assert len(unmatched)==0, "no bank credit should be left stranded or double-reserved"

print("SETTLEMENT DEDUP AND BANK IDENTITY V27 PASS")
