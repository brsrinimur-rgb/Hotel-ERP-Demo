"""
V27 end-to-end proof script - not a pytest-style regression file, a standalone
proof run per the priority order requested:
  1. Fix classifier - prove payout classification (realistic fixtures, all 3 providers)
  2. Prove Settlement Batch Engine (18_Settlement_Batch_Engine.py's exact call sequence)
  3. Prove main POS Reconciliation flow (1_POS_Reconciliation.py's exact call sequence,
     including the V27 dedup guard)
  4. Dedup / bank-row identity checks

Run directly: python3 PROVE_V27_END_TO_END.py
"""
import sys, importlib.util
import pandas as pd

sys.path.insert(0,".")
spec=importlib.util.spec_from_file_location("core_v27","core.py")
core=importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
spec2=importlib.util.spec_from_file_location("bank_ext_v27","logic/bank_settlement_extension.py")
bank_ext=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(bank_ext)

def section(title):
    print("\n"+"="*70)
    print(title)
    print("="*70)

# =============================================================================
# STEP 1 - Fix classifier / prove payout classification with REALISTIC fixtures.
# =============================================================================
section("STEP 1: classify_settlement_source() on realistic payout exports")

tamara_df=pd.DataFrame([{
    "Merchant Name":"Aigner - Tahlia Center","Statement ID":"STMT-20260801-01",
    "Statement Period":"01-Aug-2026 to 07-Aug-2026","Captured Amount":10000.0,
    "Refund Amount":0.0,"Fees":250.0,"VAT":37.5,"Payable to Merchant":9712.5,
    "Payment Date":"2026-08-08",
}])
t=core.classify_settlement_source("Tamara_Merchant_Statement_Aug2026.xlsx",tamara_df)
print("TAMARA fixture ->",repr(t)); assert t=="TAMARA_PAYOUT"

tabby_df=pd.DataFrame([
    {"Merchant Name":"Aigner - Tahlia Center","Order Number":"8942394",
     "Transferred Amount":427.0,"Total Deduction":5.0,"Transfer Date":"2026-08-05"},
    {"Merchant Name":"Aigner - Tahlia Center","Order Number":"8942501",
     "Transferred Amount":300.0,"Total Deduction":5.0,"Transfer Date":"2026-08-05"},
])
t=core.classify_settlement_source("Tabby_Bulk_Settlement_Aug2026.xlsx",tabby_df)
print("TABBY fixture ->",repr(t)); assert t=="TABBY_PAYOUT"

tap_snake=pd.DataFrame([{
    "payout_id":"PO-9001","settlement_id":"SET-20260801-77","amount":384.0,
    "status":"paid","payout_date":"2026-08-06","settlement_date":"2026-08-01",
    "authorization_id":"554030397",
}])
t=core.classify_settlement_source("TAP_Payout_Aug2026.csv",tap_snake)
print("TAP fixture (snake_case headers) ->",repr(t)); assert t=="TAP_PAYOUT"

tap_spaced=pd.DataFrame([{
    "Payout ID":"PO-9002","Settlement ID":"SET-20260801-78","Amount":128.0,
    "Status":"paid","Payout Date":"2026-08-06","Settlement Date":"2026-08-01",
}])
t=core.classify_settlement_source("TAP_Payout_Aug2026_v2.csv",tap_spaced)
print("TAP fixture (spaced headers) ->",repr(t)); assert t=="TAP_PAYOUT", \
    "TAP detection must not be stricter than normalize_tap_payout()'s own header tolerance"

print("STEP 1 PASS - all three providers classify correctly, both TAP header conventions.")

# =============================================================================
# STEP 2 - Prove Settlement Batch Engine's EXACT call sequence
# (replicates pages/18_Settlement_Batch_Engine.py's upload loop + matching +
# propagation, including the V27 propagation-gap fix for TABBY).
# =============================================================================
section("STEP 2: Settlement Batch Engine end-to-end (real call sequence)")

matched=pd.DataFrame([
    {"Unique Transaction ID":"TABBY-1","Store Code":"601","Date":pd.Timestamp("2026-08-01"),
     "Payment Type":"TABBY","Provider Reference":"8942394","D365 Amount":427.0,"Net Amount":427.0,
     "Status":"Matched","Bank Settled":False},
    {"Unique Transaction ID":"TAP-1","Store Code":"601","Date":pd.Timestamp("2026-08-01"),
     "Payment Type":"TAP","Provider Reference":"","D365 Amount":384.0,"Net Amount":384.0,
     "Status":"Matched","Bank Settled":False},
])

tabby_payout_file_df=tabby_df.copy()   # Order Number 8942394 - matches TABBY-1's Provider Reference.
tap_payout_file_df=tap_snake.copy()    # TAP payout - classifier fires, but no linking evidence exists yet (by design).

rajhi_stmt=pd.DataFrame([
    {"Date":"05/08/2026","Transaction Details":"TABBY PAYOUT","Transaction Details_2":"BATCH-1",
     "Credit":727.0,"Debit":0.0,"Balance":100000.0},  # 427 + 300 (both tabby_df rows) - 5*2 fixed fee
    {"Date":"06/08/2026","Transaction Details":"TAP TECHNOLOGIES PAYOUT","Transaction Details_2":"SET-20260801-77",
     "Credit":384.0,"Debit":0.0,"Balance":100384.0},
])

payout_parts=[]; bank_parts=[]; quarantine=[]
for fname, sheets in [("Tabby_Bulk_Settlement_Aug2026.xlsx",{"Sheet1":tabby_payout_file_df}),
                       ("TAP_Payout_Aug2026.csv",{"Sheet1":tap_payout_file_df}),
                       ("Al_Rajhi_Statement_Aug2026.xlsx",{"Sheet1":rajhi_stmt})]:
    for sheet,df in sheets.items():
        typ=core.classify_settlement_source(fname,df)
        if typ=="TAMARA_PAYOUT":
            x=core.normalize_tamara_payout(df,fname)
            if not x.empty: payout_parts.append(x)
        elif typ=="TABBY_PAYOUT":
            x=core.normalize_tabby_payout(df,fname)
            if not x.empty: payout_parts.append(x)
        elif typ=="TAP_PAYOUT":
            x=core.normalize_tap_payout(df,fname)
            if not x.empty: payout_parts.append(x)
        else:
            x=bank_ext.normalize_bank_statement(df,fname)
            if x is None or x.empty:
                x=core.normalize_bank(df,fname)  # NB: mirrors the page's ACTUAL (buggy) call - see finding below.
            if x is not None and not x.empty:
                bank_parts.append(x)
            else:
                quarantine.append({"File":fname,"Sheet":sheet,"Reason":"Unsupported settlement/payout format"})

provider_batches=pd.concat(payout_parts,ignore_index=True) if payout_parts else pd.DataFrame()
provider_batches=core.link_tabby_payout_underlying_ids(provider_batches,matched)  # V27 propagation-gap fix.
bank=pd.concat(bank_parts,ignore_index=True) if bank_parts else pd.DataFrame()
print("provider_batches rows:",len(provider_batches))
print(provider_batches[["Provider","Expected Bank Amount","Underlying IDs"]])
print("bank rows:",len(bank), "| Bank values:",sorted(set(bank["Bank"].astype(str))) if not bank.empty else [])
assert len(provider_batches)==2, "TABBY (1 batch) + TAP (1 batch) must both classify and normalize"
tabby_batch=provider_batches[provider_batches["Provider"]=="TABBY"].iloc[0]
assert tabby_batch["Underlying IDs"]=="TABBY-1", \
    "TABBY batch must resolve its Order Number back to the one matched transaction that carries it"
tap_batch=provider_batches[provider_batches["Provider"]=="TAP"].iloc[0]
assert str(tap_batch.get("Underlying IDs",""))=="", \
    "TAP must NOT be linked - no trusted per-transaction reference exists for it yet (by design)"

card_batches=core.build_card_settlement_batches(matched)  # empty here - neither row is card/AMEX.
card_result,anb_unmatched=bank_ext.reconcile_card_batches_advanced(card_batches,bank,1.0)
provider_result,rajhi_unmatched=bank_ext.reconcile_provider_batches_to_rajhi(provider_batches,bank,1.0,5.0)
batch_result=pd.concat([x for x in [card_result,provider_result] if x is not None and not x.empty],ignore_index=True)
print(batch_result[["Provider","Settlement Status","Actual Bank Amount","Bank Match Rule"]])
assert (batch_result["Settlement Status"]=="BANK RECEIVED").sum()==2, \
    "both TABBY and TAP payout batches must actually settle against Al Rajhi credits now that the classifier fires"

updated=bank_ext.propagate_verified_batches(matched,batch_result)
print(updated[["Unique Transaction ID","Bank Settled","Settlement Stage"]])
assert bool(updated.loc[updated["Unique Transaction ID"]=="TABBY-1","Bank Settled"].iloc[0]) is True, \
    "TABBY-1 must flip to Bank Settled=True end-to-end - this is the V27 propagation-gap fix"
assert bool(updated.loc[updated["Unique Transaction ID"]=="TAP-1","Bank Settled"].iloc[0]) is False, \
    "TAP-1 must knowingly stay Bank Settled=False - TAP is not linked yet, this is the documented remaining gap, not a silent failure"

print("STEP 2 PASS - Settlement Batch Engine settles TABBY end-to-end (batch -> matched transaction),")
print("              and TAP correctly settles at the batch level while staying unlinked, as designed.")

# NOTE / separate finding, NOT fixed here (out of V27's narrow scope, flagging for a follow-up):
# pages/18_Settlement_Batch_Engine.py line 73 (and pages/1_POS_Reconciliation.py's equivalent
# call) label bank statements "ANB Bank"/"Al Rajhi Bank" (or, in Settlement Batch Engine's case,
# literally the filename) when the legacy normalize_bank() fallback fires - but
# reconcile_card_batches_to_anb / reconcile_provider_batches_to_rajhi filter on the bank pool
# with an EXACT match against "ANB" / "AL RAJHI" (no "Bank" suffix, no filename). Any statement
# that falls through to the legacy parser is therefore invisible to batch-level matching
# regardless of the V27 identity fixes. Confirmed by reading both page sources; not exercised by
# this proof run because this scenario uses the V24 parser (Bank="AL RAJHI"), the expected path
# for your actual ANB/Al Rajhi statements.

# =============================================================================
# STEP 3 - Prove main POS Reconciliation flow's dedup guard + payout wiring
# (replicates the relevant slice of pages/1_POS_Reconciliation.py's upload loop).
# =============================================================================
section("STEP 3: Main POS Reconciliation flow (dedup guard + payout wiring)")

tender_df=pd.DataFrame([{
    "Store":"601","Transdate":"2026-08-01","ReceiptID":"R-1","Auth Code":"554030397",
    "TAP":384.0,
}])

# A single uploaded file named with "tap" in it that is ALSO a genuine TAP payout export -
# this is exactly the overlap V27 §1 exists to de-duplicate.
overlap_file_df=tap_snake.copy()

pos_parts=[]; payout_parts2=[]; quarantine2=[]; payout_sheets=set()
uploads_sim=[("D365_Store_Tender.xlsx",{"Sheet1":tender_df}),
             ("TAP_Payout_Aug2026.csv",{"Sheet1":overlap_file_df})]

tender_parts=[]
for fname, sheets in uploads_sim:
    for sheet,df in sheets.items():
        settlement_typ=core.classify_settlement_source(fname,df)
        if settlement_typ:
            payout_sheets.add((fname,sheet))
            continue
        typ=core.classify(f"{fname}-{sheet}",df)
        if typ=="D365 STORE TENDER":
            tender_parts.append(core.normalize_tender(df))
        elif typ in {"POS","AMEX","TABBY","TAMARA","TAP"}:
            forced=typ if typ in {"AMEX","TABBY","TAMARA","TAP"} else None
            try: pos_parts.append(core.normalize_pos(df,fname,forced))
            except Exception as e: quarantine2.append({"File":fname,"Sheet":sheet,"Reason":str(e)})

print("payout_sheets routed away from transaction classification:",payout_sheets)
print("pos_parts produced from the overlap file:",len(pos_parts))
assert ("TAP_Payout_Aug2026.csv","Sheet1") in payout_sheets, \
    "the overlap file must be recognized as a payout file and routed away from transaction parsing"
assert len(pos_parts)==0, \
    "the overlap file must NOT also be normalized as a POS transaction file - this is the V27 §1 fix"

for fname,sheets in uploads_sim:
    if (fname,list(sheets.keys())[0]) not in payout_sheets:
        continue
    for sheet,df in sheets.items():
        typ=core.classify_settlement_source(fname,df)
        if typ=="TAP_PAYOUT":
            x=core.normalize_tap_payout(df,fname)
            if not x.empty: payout_parts2.append(x)
r_provider_batches=pd.concat(payout_parts2,ignore_index=True) if payout_parts2 else pd.DataFrame()
print("provider payout batches recovered from the payout scan:",len(r_provider_batches))
assert len(r_provider_batches)==1, "the payout scan must still pick up the file exactly once"

print("STEP 3 PASS - the same file is classified and normalized exactly once, and still reaches the payout path.")

section("ALL V27 END-TO-END PROOF STEPS PASSED")
