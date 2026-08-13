# RetailRecon AI — V30: ANB Settlement Lag Offset & Terminal ID Normalization

Two of the four next-patch items recommended in the July 2026 real-data findings, built and verified against the same real production files, not synthetic fixtures. The third recommended item (AMEX) turned out, on investigation, to be a different and larger problem than first described — see §3, not fixed here. The fourth (re-send the missing July 11 file) isn't a code change and is still open on your side.

## 1. ANB settlement-lag offset

**Problem, confirmed on real data:** `reconcile_card_batches_to_anb()` / `reconcile_card_batches_advanced()` (`logic/bank_settlement_extension.py`) compared each card settlement batch's date (the POS transaction date) directly against the date embedded in the ANB bank narration, with no adjustment. Tested directly against your real July statement: this produced **0 exact matches across 707 correctly-formatted batches**. ANB actually books the bank credit for a given day's terminal batch under the *next* calendar day's narration date — shifting the comparison forward by exactly one day produced **446 exact matches (63%)** on the same data.

**Fix:** both functions now take a `settlement_lag_days` parameter (default `1`), applied to the Settlement Date before comparing against the bank narration's Source Date. Default `1` matches the confirmed real-data pattern; it's a parameter, not a hardcoded assumption, so it can be tuned or set to `0` if a different ANB statement cycle is ever observed. Exposed as a "ANB settlement lag (days)" input on both `pages/1_POS_Reconciliation.py` (the main RUN RECONCILIATION path, which already calls this matching logic) and `pages/18_Settlement_Batch_Engine.py`.

## 2. Terminal ID normalization for `traf_09582037.xlsx`

**Problem, confirmed on real data:** `traf_09582037.xlsx`'s `terminal_id` column stores the real 8-digit ANB terminal code with a constant 8-digit suffix appended (e.g. `5561069001300000` for terminal `55610690`, suffix always `01300000` across every affected row checked). ANB's own bank narration only ever uses the bare 8-digit code, so these Terminal IDs could never match regardless of the date fix. 95 of 802 real card batches (SAR 469,033) carried this shape, all traced to this one file.

**Fix (`core.py`):** new `_normalize_anb_pos_terminal_id()` helper, applied where Terminal ID is captured in `normalize_pos()`. Strips the known 16-digit/`01300000`-suffix shape back to the 8-digit code; any other shape (any other file's Terminal ID) passes through completely unchanged.

## 3. AMEX — correction to the original recommendation, not fixed

The July findings report recommended "add AMEX to the bank narration scheme-detection pattern" as a quick fix. That was wrong, and I want to be direct about it rather than quietly build around it. Before writing this patch I went back to the raw ANB statement to confirm what an AMEX credit's narration actually looks like — and AMEX doesn't go through the terminal-batch narration pattern (`MID_TID_ddmmyy` / `SCHEME_VAT_FEE_TX_n`) at all. It settles as a separate SIBC inter-bank wire transfer from "Amex (Saudi Arabia) Ltd." with no terminal ID, no scheme code, and no per-terminal breakdown in the narration whatsoever — just a wire reference number.

I also checked whether it's at least a clean 1-wire-per-day sum of that day's AMEX POS batches — it isn't. July 13's wire is SAR 19,676.88 against a same-day AMEX POS sum of SAR 15,000.00; July 15's wire is SAR 14,482.50 against a same-day sum of SAR 40,900.00. No consistent 1:1 or per-day aggregation relationship is visible from the data alone.

This means AMEX settlement is, structurally, an instance of the many-POS-batches-to-one-bank-credit problem — already tracked as an open item in the V27 governance decision, where you were explicit: *"That needs its own controlled matching design because we should not solve it by broad amount aggregation."* Building an AMEX-specific aggregation shortcut here would be exactly the kind of guess that instruction rules out. I'm leaving AMEX unfixed and recommending it be folded into that same open item rather than treated as a separate quick patch.

## 4. Verification performed — real data, before/after

Re-ran the full pipeline against the same real July 2026 files (D365 Store Tender, D365 Sales Details, `traf_09582037.xlsx`, 24 daily United Luxury POS exports, Tabby/Tamara/TAP files, ANB + Al Rajhi statements) with the patched code:

| Metric | Before V30 | After V30 |
|---|---|---|
| Card/AMEX settlement batches | 802 | 785 (fewer, larger batches — terminal ID normalization now correctly groups previously-split traf_ rows) |
| Card batches: BANK RECEIVED | 0 | **446** |
| Card batches: BANK REVIEW REQUIRED | 527 | 259 |
| Card batches: BANK RECEIPT PENDING | 275 | 80 |
| Matched transactions with Bank Settled = True | 762 / 3,818 (20%) | **2,159 / 3,818 (57%)** |
| Settlement Stage = BANK RECEIVED | 220 | **1,920** |

Of the 80 remaining PENDING batches: 65 fall on July 30–31 (the ANB statement's narration data only runs through July 30, so the +1-day-shifted match for July 31 batches has nothing to compare against — a statement-coverage edge, not a code gap), and 17 are AMEX (see §3). Of the 259 remaining REVIEW REQUIRED batches (SAR 1,339,088), a unique bank-narration candidate is found but the dollar amount doesn't reconcile — consistent with the same already-tracked many-batches-to-one-credit item, not a new defect; not investigated further here since it's explicitly out of scope for a quick patch per your prior instruction.

Provider (Tabby/Tamara/TAP) payout batches are untouched by this patch, as expected — 57/134 BANK RECEIVED before and after.

`python3 -m py_compile` clean on all four changed files.

## Files delivered

- `logic/bank_settlement_extension.py` — patched (`settlement_lag_days` parameter, default 1).
- `core.py` — patched (`_normalize_anb_pos_terminal_id()`).
- `pages/1_POS_Reconciliation.py` — patched (new sidebar input, passed through to the main reconciliation path's card-matching call).
- `pages/18_Settlement_Batch_Engine.py` — patched (same new input, independent of the main page's session state).

## Still open

- AMEX settlement matching (§3 above) — folded into the existing many-batches-to-one-credit open item, needs its own controlled design.
- The two other items already tracked in the V27 governance decision: Tamara/TAP transaction-level linking, and the legacy bank-parser label mismatch.
- The missing `20260711_221227_UNITED_LUXURY_Transactions_Report.xlsx` file — still needs to be re-sent; this patch doesn't create data that isn't there.
