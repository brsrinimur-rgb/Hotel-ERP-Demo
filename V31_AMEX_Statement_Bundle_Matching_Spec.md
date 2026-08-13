# RetailRecon AI — V31: AMEX Statement Bundle Matching

You uploaded the AMEX Saudi Arabia "Statement of account" export (`SE2026_07_319710107967.xlsx`) — the exact evidence the V30 spec said was needed to solve AMEX settlement properly instead of guessing. This patch uses it.

## What the statement contains, and why AMEX needed different handling

AMEX doesn't settle through the per-terminal ANB card narration at all (confirmed in V30). Its own statement export shows why: it's a running ledger of "Submission" rows (one per card transaction, with Terminal Number, Date, gross Amount and net CR) interleaved with "Payment" rows ("Sarie payment made" — an actual bank wire, with the wired amount). A single wire routinely bundles submissions from **multiple terminals across multiple days** into one payment — e.g. your July 18 statement bundles a terminal-55610692 sale and a terminal-55610704 sale, paid together on July 19. That's structurally incompatible with matching one terminal's one day against one bank credit, which is all the ANB card-matching rule (V29/V30) can do.

## What this patch adds

**`core.is_amex_statement_file()` / `core.normalize_amex_statement()`:** detects the AMEX statement by its "Submissions" sheet shape and parses it into two frames — one row per Payment (wire date + the statement's own wired amount) and one row per Submission (Terminal, Date, gross Amount), each submission tagged with which Payment it was bundled into. Wired both into `pages/1_POS_Reconciliation.py` (the main RUN RECONCILIATION path) and `pages/18_Settlement_Batch_Engine.py`, mirroring how AMEX statement files are handled specially — a whole file at once, not sheet-by-sheet — the same way payout files already are.

**`logic/bank_settlement_extension.py`: `reconcile_amex_batches_via_statement()`:** for every AMEX card settlement batch still not resolved by the per-terminal ANB pass, this:
1. Finds the statement Submissions matching that batch's Terminal + Date, and only proceeds if they fully account for the batch's own gross amount (no partial or ambiguous matches — ever).
2. Groups every batch that resolves to the same statement Payment, and only proceeds if the **gross** amounts on both sides — the statement's own submissions and our batches — agree exactly (deliberately gross-to-gross, never comparing our approximate net/commission estimate against AMEX's actual fee schedule, which are computed independently and were never going to agree to the SAR).
3. Only then looks for a matching real ANB bank credit (Provider=AMEX, amount within tolerance, dated within a few days of the wire) — and only settles the whole bundle if exactly one bank row matches.

Any batch that fails any of these checks is left exactly as the ANB per-terminal pass already set it. This is real accounting evidence from AMEX's own ledger, not the broad-amount-aggregation shortcut the V27 governance decision ruled out — every step requires an exact, unambiguous match, and nothing is settled by fitting our own numbers to a target total.

**Also added:** `parse_anb_narration()` now tags an ANB bank row as `Provider=AMEX` when its narration text names "Amex" (previously these wire rows sat completely untagged in the bank data), which is what lets the new function find them.

## Verified against real data

Re-ran the full pipeline with the AMEX statement included: **12 of 17 AMEX settlement batches now resolve to BANK RECEIVED** (SAR 140,365), up from 0. Total matched transactions with a confirmed bank receipt: **2,170 / 3,818**, up from 2,159 after V30 and 762 originally.

The 5 AMEX batches still not resolved break down cleanly, and each is a correct refusal to guess, not a gap in the logic:

- **2 batches** (dated July 30) were bundled into wires made July 30–31, which fall outside the ANB statement's date coverage — the same month-end edge already identified in V30.
- **1 batch** (July 31, SAR 77,000) is marked `Paid = N` in AMEX's own statement — it genuinely hasn't been paid out yet, confirmed by AMEX's own book, not a defect in this reconciliation.
- **2 batches** (July 18 and July 24) sit in a wire that also bundles a submission from a terminal/date our own POS-to-D365 reconciliation has **no matching transaction for at all** — e.g. the July 18 wire's statement evidence includes a terminal-55610692 sale (SAR 18,000) that never appears in `matched`. The completeness check correctly refuses to settle either bundled batch until that gap is explained, rather than settling just the batch it can see and silently ignoring the other. This is a real finding worth chasing on your side — either that terminal's transaction is missing from the POS files supplied, or it landed in `matched` under a different payment type/terminal mapping than expected.

## Files delivered

- `core.py` — patched (`is_amex_statement_file()`, `normalize_amex_statement()`).
- `logic/bank_settlement_extension.py` — patched (`parse_anb_narration()` AMEX tagging, `reconcile_amex_batches_via_statement()`).
- `pages/1_POS_Reconciliation.py` — patched (AMEX statement detection wired into the main run).
- `pages/18_Settlement_Batch_Engine.py` — patched (same, for the standalone settlement page).
- Re-run reconciliation workbook (`RetailRecon_Real_Reconciliation_Report_Jul2026_PostV31Patch.xlsx`), including new AMEX Statement Payments / Submissions tabs.

`python3 -m py_compile` clean on all four changed files.

## Still open

- The July 18 / July 24 "missing counterpart transaction" finding above — worth investigating on your side before it's treated as resolved.
- The two dates outside ANB statement coverage — resend a fuller ANB statement (through early August) if you want those closed too.
- The two items already tracked in the V27 governance decision (Tamara/TAP transaction-level linking, legacy bank-parser label mismatch) and the missing July 11 United Luxury Corp POS file — none touched by this patch.
