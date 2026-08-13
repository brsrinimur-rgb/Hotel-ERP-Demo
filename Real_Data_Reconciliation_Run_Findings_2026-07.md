# RetailRecon AI — Real-Data Reconciliation Run: Results & Findings
**Period:** 2026-07-01 to 2026-07-31 | **Entities:** Aigner KSA - Online, United Luxury Corp | **Run date:** 2026-08-13

This is the actual V27/V28-patched reconciliation engine run against your real uploaded files — D365 Store Tender, D365 Sales Details, ANB POS terminal exports (`traf_09582037.xlsx` + 24 daily `UNITED_LUXURY_Transactions_Report` files), Tabby/Tamara/TAP transaction and payout files, and the ANB + Al Rajhi bank statements. 41 main files plus 2 bank statements were processed. Full results are in the attached workbook; this document explains what happened and why, including four anomalies worth your attention before you treat these numbers as final.

## Headline results

Transaction-level match (D365 Store Tender against POS/provider records): **3,818 matched** (3,810 clean + 8 flagged Review), **1,112 unmatched on the D365 side**, **1,612 unmatched on the POS/provider side** — a 77.4% match rate. 460 cash tender rows were correctly excluded from card/provider matching.

Bank settlement (matched transactions confirmed against an actual bank credit): **762 of 3,818 matched transactions (20%)** carry a confirmed bank receipt so far. The rest sit at "TRANSACTION MATCHED" — reconciled to the sale, not yet proven to the bank statement. That 20% is lower than it should be, and almost all of the shortfall traces to one specific, well-understood cause below — not to the underlying data being wrong.

## 1. Missing file — a full day of United Luxury Corp POS data

You referenced a file named `20260711_221227_UNITED_LUXURY_Transactions_Report.xlsx` in the upload conversation, but it never actually landed on disk — I confirmed this by listing every file that did arrive. Every other day from July 5 through August 2 is present (including two files for July 12), but July 11 has no POS terminal export for United Luxury Corp. Any July 11 United Luxury Corp POS transactions in this run are therefore reconciled only from the ANB terminal-level file (`traf_09582037.xlsx`), not from the richer daily export — worth re-sending that file to close the gap.

## 2. Why 0 of 802 card/AMEX settlement batches reached BANK RECEIVED

This is the anomaly that matters most, so I traced it to source rather than reporting the symptom. Three distinct, independently-confirmed causes, all inside the ANB card-matching step — nothing wrong with the underlying transactions or the bank statement itself:

**a) A one-day settlement lag the matching rule doesn't account for (the majority cause).** The engine compares each settlement batch's date (the POS transaction date) directly against the date embedded in the ANB bank narration. I tested this directly: matching with no date adjustment produces **zero** exact matches across 707 correctly-formatted batches. Shifting the comparison forward by exactly one day produces **446 exact matches (63%)** on the same data. In other words, ANB books the bank credit for a given day's terminal batch under the *next* calendar day's narration date, and the current matching rule doesn't allow for that lag. This is a one-line rule fix, not a data problem — I did not apply it in this run, since a fix like this should go through the same spec-and-test process as V27/V28, but it's the clear next-patch candidate.

**b) A terminal ID format mismatch, isolated to one file.** 95 of the 802 batches (SAR 469,033) carry a 16-digit Terminal ID (e.g. `5561069001300000`), all traced to `traf_09582037.xlsx`'s `terminal_id` column, which appends a constant `01300000` suffix to the real 8-digit ANB terminal code. The bank's own narration only ever uses the 8-digit code, so these 95 batches can never match regardless of the date-lag fix — the suffix needs to be stripped when this file's Terminal ID is normalized.

**c) AMEX transactions are never recognized in the bank narration parser.** All 17 AMEX settlement batches found zero bank-side candidates, at any date offset. The narration parser's scheme-detection pattern only recognizes `MADA`, `VC` (Visa), and `MC` (Mastercard) — there's no AMEX case in that pattern, so an AMEX credit's scheme is never tagged and it can never be selected as a candidate.

A secondary, less certain pattern: of the batches that still don't match exactly even after the one-day shift, credits dated Friday or Saturday (the Saudi banking weekend) are somewhat over-represented (85 of 181), consistent with weekend transactions sometimes being batched together into one later credit rather than settling day-by-day. This needs a closer look before it's treated as confirmed, unlike (a)–(c) above which are proven.

None of this affects the Tabby/Tamara/TAP provider path, which doesn't share this date-matching rule — that's why provider payouts already achieved 57 of 134 batches at BANK RECEIVED in this same run.

## 3. Tamara payout batch structure — expected, not a defect

I flagged this as an open question before analyzing it properly; having now read the raw Tamara invoice files directly, it's correct behavior. Tamara's own weekly invoice statement is genuinely structured as six rows per invoice — one per payment-plan type (Pay By Later, Pay Next Month, Pay In Installment, Pay in Full, Settlement Fee, Credit Total) — each with its own "Payable to Merchant" figure. Several show SAR 0.00 simply because no orders used that plan type in that period; that's the real statement, not a parsing error. The one genuine gap: Tamara's summary table has no per-row date column (the period only appears in the filename), so `Settlement Date` comes through as blank for every Tamara batch. I checked whether this weakens matching — it doesn't: when the date is blank, the provider-matching rule correctly falls back to matching by provider and amount across the full bank statement instead of narrowing by date, so Tamara's results in this run are not compromised by it. Still worth hardening later by parsing the period date out of the filename.

## 4. One quarantined file/sheet

`20260707_141936_UNITED_LUXURY_Transactions_Report.xlsx`, sheet "Sheet2", classified as UNKNOWN and was excluded rather than guessed at. This is a single sheet, not a whole day's data loss — the same file's other sheet processed normally.

## What this means for month-end

The transaction-level reconciliation (D365 to POS/provider, 77.4% match) is sound and ready to work from. The 20% bank-settlement rate is artificially low because of the three card-matching causes in §2, not because the bank hasn't actually paid — once (a) and (b) are patched, I'd expect the large majority of the 527 "Review Required" card batches to resolve to BANK RECEIVED on a re-run against the same files, since the underlying evidence (unique terminal+date+scheme bank rows) is already present. I'd treat the current 762 Bank Settled count as a floor, not a ceiling.

## Files delivered

- `RetailRecon_Real_Reconciliation_Report_Jul2026.xlsx` — Summary, Matched, Unmatched D365, Unmatched POS, Card Settlement Batches (with per-batch Settlement Status and Review Reason), Provider Payout Batches, Bank (all ANB + Al Rajhi rows), Quarantine.
- This findings document.

## Recommended next patch (not built yet — pending your go-ahead)

1. Add a configurable settlement-lag offset (default +1 day) to the ANB card-matching date comparison.
2. Normalize `traf_09582037.xlsx`'s Terminal ID by stripping the trailing `01300000` suffix during POS normalization.
3. Add AMEX to the bank narration scheme-detection pattern.
4. Re-send the missing July 11 United Luxury Corp POS file.

These are new findings from this run, separate from the three items already tracked as open in the V27 governance decision (Tamara/TAP transaction linking, the legacy bank-parser label mismatch, and many-batches-to-one-credit aggregation) — none of today's findings touch those three.
