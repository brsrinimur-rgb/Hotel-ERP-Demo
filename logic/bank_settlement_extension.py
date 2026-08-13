
"""
RetailRecon V24 — additive bank settlement propagation extension.
V27 — bank-row identity is now fully deterministic (Source File + Source
Sheet + Source Row + Bank Date + Bank Amount); narration text is evidence
used for matching only, never part of a row's identity.

This module does not delete or replace core.py settlement logic. It adds:
- robust ANB / Al Rajhi statement normalization for the Finance-supplied formats;
- bank-narration parsing for terminal, merchant, scheme, source date and TX count;
- strong batch-level bank matching;
- propagation of verified bank settlement evidence back to matched transactions.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

def _txt(v):
    if v is None or (isinstance(v,float) and pd.isna(v)):
        return ""
    return str(v).strip()

def _num(v):
    try:
        x=pd.to_numeric(pd.Series([v]),errors="coerce").iloc[0]
        return np.nan if pd.isna(x) else float(x)
    except Exception:
        return np.nan

def _norm_payment(v):
    s=_txt(v).upper().replace(" ","")
    if s in {"MADA","P","P1"}: return "MADA"
    if s in {"VISA","VC","VISACARD"}: return "VISA"
    if s in {"MASTER","MC","MASTERCARD"}: return "MASTERCARD"
    if s in {"AMEX","AX"}: return "AMEX"
    if s=="TABBY": return "TABBY"
    if s=="TAMARA": return "TAMARA"
    if s=="TAP": return "TAP"
    return _txt(v).upper()

def _parse_ddmmyy(s):
    s=_txt(s)
    m=re.fullmatch(r"(\d{2})(\d{2})(\d{2})",s)
    if not m:return pd.NaT
    dd,mm,yy=m.groups()
    return pd.to_datetime(f"20{yy}-{mm}-{dd}",errors="coerce")

def parse_anb_narration(parts):
    raw=" | ".join(_txt(x) for x in parts if _txt(x))
    terminal=""
    merchant=""
    source_date=pd.NaT
    scheme=""
    tx_count=np.nan
    fee=np.nan
    vat=np.nan

    # Example:
    # 301128607335_55610715_300626
    # VC_15.78_105.09_TX_12
    m=re.search(r"\b(\d{8,20})_(\d{6,20})_(\d{6})\b",raw)
    if m:
        merchant=m.group(1)
        terminal=m.group(2)
        source_date=_parse_ddmmyy(m.group(3))

    m=re.search(r"\b(MADA|VC|MC)_([0-9.]+)_([0-9.]+)_TX_(\d+)\b",raw,re.I)
    if m:
        scheme=_norm_payment(m.group(1))
        # Finance statement pattern shows VAT then commission/fee.
        vat=_num(m.group(2))
        fee=_num(m.group(3))
        tx_count=int(m.group(4))

    provider="ANB POS" if scheme in {"MADA","VISA","MASTERCARD"} else ""
    return {
        "Provider":provider,
        "Narration Scheme":scheme,
        "Narration Terminal ID":terminal,
        "Narration Merchant ID":merchant,
        "Narration Source Date":source_date,
        "Narration Transaction Count":tx_count,
        "Narration Fee":fee,
        "Narration VAT":vat,
        "Description":raw,
    }

def normalize_bank_statement(df, source_file=""):
    """
    Normalize the two real statement formats supplied by Finance.

    ANB:
      Trans: Date, Amount Dr., Amount Cr., Narration, Narration 1..3
    Al Rajhi:
      Date, Transaction Details, Transaction Details_2, Credit, Debit, Balance
    """
    if df is None or df.empty:
        return pd.DataFrame()

    d=df.copy()
    cols={str(c).strip().lower():c for c in d.columns}

    # ANB
    if "trans: date" in cols and ("amount cr." in cols or "amount cr" in cols):
        dc=cols["trans: date"]
        cr=cols.get("amount cr.",cols.get("amount cr"))
        dr=cols.get("amount dr.",cols.get("amount dr"))
        narr_cols=[c for c in d.columns if str(c).strip().lower().startswith("narration")]
        rows=[]
        for i,r in d.iterrows():
            credit=_num(r.get(cr))
            debit=_num(r.get(dr)) if dr else 0.0
            credit=0.0 if pd.isna(credit) else credit
            debit=0.0 if pd.isna(debit) else debit
            amt=credit-debit
            if amt==0: continue
            evidence=parse_anb_narration([r.get(c) for c in narr_cols])
            rows.append({
                "Bank":"ANB",
                "Bank Date":pd.to_datetime(r.get(dc),errors="coerce"),
                "Bank Amount":amt,
                "Credit":credit,
                "Debit":debit,
                "Bank Source File":source_file,
                "Bank Source Row":i+1,
                **evidence,
            })
        return pd.DataFrame(rows)

    # Al Rajhi
    if "date" in cols and "credit" in cols and "debit" in cols:
        dc=cols["date"]; cr=cols["credit"]; dr=cols["debit"]
        detail_cols=[c for c in d.columns if str(c).strip().lower().startswith("transaction details")]
        rows=[]
        for i,r in d.iterrows():
            credit=_num(r.get(cr)); debit=_num(r.get(dr))
            credit=0.0 if pd.isna(credit) else credit
            debit=0.0 if pd.isna(debit) else debit
            amt=credit+debit if debit<0 else credit-debit
            if amt==0: continue
            desc=" | ".join(_txt(r.get(c)) for c in detail_cols if _txt(r.get(c)))
            u=desc.upper()
            provider=""
            if "TABBY" in u: provider="TABBY"
            elif "TAMARA" in u: provider="TAMARA"
            elif re.search(r"\bTAP\b",u) or "TAP TECHNOLOGIES" in u: provider="TAP"
            elif "AMEX" in u or "AMERICAN EXPRESS" in u: provider="AMEX"
            rows.append({
                "Bank":"AL RAJHI",
                "Bank Date":pd.to_datetime(r.get(dc),dayfirst=True,errors="coerce"),
                "Bank Amount":amt,
                "Credit":credit,
                "Debit":debit,
                "Bank Source File":source_file,
                "Bank Source Row":i+1,
                "Provider":provider,
                "Description":desc,
                "Narration Scheme":"",
                "Narration Terminal ID":"",
                "Narration Merchant ID":"",
                "Narration Source Date":pd.NaT,
                "Narration Transaction Count":np.nan,
                "Narration Fee":np.nan,
                "Narration VAT":np.nan,
            })
        return pd.DataFrame(rows)

    return pd.DataFrame()

def _enhance_card_batches(batches):
    if batches is None or batches.empty:
        return pd.DataFrame()
    x=batches.copy()
    x["Payment Type"]=x.get("Payment Type","").apply(_norm_payment)
    x["Settlement Date"]=pd.to_datetime(x.get("Settlement Date"),errors="coerce").dt.normalize()
    x["Terminal ID"]=x.get("Terminal ID","").fillna("").astype(str).str.strip()
    x["Expected Bank Amount"]=pd.to_numeric(x.get("Expected Bank Amount",0),errors="coerce").fillna(0.0)
    x["Transaction Count"]=pd.to_numeric(x.get("Transaction Count",np.nan),errors="coerce")
    return x


def _bank_row_key(row):
    """
    V27: fully deterministic bank-row identity.

    Source File + Source Sheet + Source Row + Bank Date + Bank Amount together
    identify a single physical bank statement row. Narration/description text
    is never part of the identity - it is evidence used for matching, not for
    telling two bank rows apart. Both the V24+ ANB/Al Rajhi parser
    (bank_settlement_extension.normalize_bank_statement) and the legacy
    fallback parser (core.normalize_bank, patched in V27) stamp Bank Source
    File / Bank Source Sheet / Bank Source Row on every row, so this key no
    longer needs a hash-based fallback for "rows with no source metadata".
    """
    return "::".join([
        _txt(row.get("Bank Source File","")),
        _txt(row.get("Bank Source Sheet","")),
        _txt(row.get("Bank Source Row","")),
        _txt(row.get("Bank Date","")),
        _txt(row.get("Bank Amount","")),
    ])

def reconcile_card_batches_to_anb(batches, bank, tolerance=1.0):
    """
    Strong ANB rule:
    Terminal + source transaction date + scheme + expected net amount.
    Transaction count is used as additional evidence when present.
    """
    x=_enhance_card_batches(batches)
    if x.empty:
        return pd.DataFrame(),bank.copy() if bank is not None else pd.DataFrame()
    b=bank.copy() if bank is not None else pd.DataFrame()
    if b.empty:
        y=x.copy(); y["Settlement Status"]="BANK RECEIPT PENDING"
        return y,b

    b=b[(b.get("Bank","").astype(str)=="ANB") & (pd.to_numeric(b.get("Credit",0),errors="coerce").fillna(0)>0)].copy()
    used=set(); rows=[]

    for _,r in x.iterrows():
        provider=str(r.get("Provider","")).upper()
        if provider not in {"ANB POS","AMEX"}:
            continue

        terminal=_txt(r.get("Terminal ID"))
        pay=_norm_payment(r.get("Payment Type"))
        sdate=pd.to_datetime(r.get("Settlement Date"),errors="coerce")
        exp=float(r.get("Expected Bank Amount",0) or 0)
        txc=pd.to_numeric(pd.Series([r.get("Transaction Count",np.nan)]),errors="coerce").iloc[0]

        cand=b[~b.index.isin(used)].copy()
        if terminal:
            cand=cand[cand["Narration Terminal ID"].astype(str).eq(terminal)]
        if pay:
            cand=cand[cand["Narration Scheme"].apply(_norm_payment).eq(pay)]
        if pd.notna(sdate):
            cand=cand[pd.to_datetime(cand["Narration Source Date"],errors="coerce").dt.normalize().eq(sdate.normalize())]
        if pd.notna(txc):
            same_count=cand[pd.to_numeric(cand["Narration Transaction Count"],errors="coerce").eq(float(txc))]
            if not same_count.empty:
                cand=same_count

        cand["_DIFF"]=(pd.to_numeric(cand["Bank Amount"],errors="coerce")-exp).abs()
        exact=cand[cand["_DIFF"]<=float(tolerance)]

        sel=None; status="BANK RECEIPT PENDING"; rule=""; reason=""
        if len(exact)==1:
            sel=exact.iloc[0]
            used.add(sel.name)
            status="BANK RECEIVED"
            rule="ANB Terminal + Source Date + Scheme + Net Amount"
        elif len(exact)>1:
            status="BANK REVIEW REQUIRED"
            reason="Multiple ANB bank credits satisfy the same settlement batch"
        elif len(cand)==1:
            # Evidence keys are unique but amount differs: keep as review, never auto-settle.
            sel=cand.iloc[0]
            status="BANK REVIEW REQUIRED"
            rule="ANB Terminal + Source Date + Scheme"
            reason=f"Unique ANB settlement evidence found but amount differs by SAR {abs(float(sel['Bank Amount'])-exp):,.2f}"

        rec=r.to_dict()
        rec.update({
            "Settlement Status":status,
            "Bank Match Rule":rule,
            "Settlement Review Reason":reason,
            "Actual Bank Amount":float(sel["Bank Amount"]) if sel is not None else np.nan,
            "Bank Date":sel["Bank Date"] if sel is not None else pd.NaT,
            "Bank Difference":round(float(sel["Bank Amount"])-exp,2) if sel is not None else np.nan,
            "Bank Reference":sel["Description"] if sel is not None else "",
            "Bank Source File":sel["Bank Source File"] if sel is not None else "",
            # V27: carry the full identity forward so a later reservation pass
            # (reconcile_card_batches_advanced) can recompute the exact same
            # deterministic key instead of re-searching for it by narration text.
            "Bank Source Sheet":sel.get("Bank Source Sheet","") if sel is not None else "",
            "Bank Source Row":sel.get("Bank Source Row","") if sel is not None else "",
        })
        rows.append(rec)

    result=pd.DataFrame(rows)
    bank_unmatched=b[~b.index.isin(used)].copy()
    return result,bank_unmatched

def reconcile_provider_batches_to_rajhi(batches, bank, tolerance=1.0, tabby_fixed_fee=5.0):
    """
    Provider payout → Al Rajhi bank receipt.
    Strong evidence: provider + date window + amount.
    Tabby additionally supports the observed configurable SAR 5 payout deduction.
    """
    if batches is None or batches.empty:
        return pd.DataFrame(),bank.copy() if bank is not None else pd.DataFrame()
    x=batches.copy()
    x=x[x.get("Provider","").astype(str).str.upper().isin(["TABBY","TAMARA","TAP"])].copy()
    if x.empty:
        return pd.DataFrame(),bank.copy() if bank is not None else pd.DataFrame()

    b=bank.copy()
    b=b[(b.get("Bank","").astype(str)=="AL RAJHI") & (pd.to_numeric(b.get("Credit",0),errors="coerce").fillna(0)>0)].copy()
    used=set(); rows=[]

    for _,r in x.iterrows():
        provider=str(r.get("Provider","")).upper()
        exp=float(r.get("Expected Bank Amount",0) or 0)
        sdate=pd.to_datetime(r.get("Settlement Date"),errors="coerce")
        cand=b[~b.index.isin(used)].copy()
        cand=cand[cand.get("Provider","").astype(str).str.upper().eq(provider)]
        if pd.notna(sdate):
            dd=(pd.to_datetime(cand["Bank Date"],errors="coerce").dt.normalize()-sdate.normalize()).dt.days
            cand=cand[(dd>=0)&(dd<=10)].copy()

        cand["_DIFF"]=(pd.to_numeric(cand["Bank Amount"],errors="coerce")-exp).abs()
        if provider=="TABBY":
            cand["_DIFF_FEE"]=(pd.to_numeric(cand["Bank Amount"],errors="coerce")-(exp-tabby_fixed_fee)).abs()
            cand["_BEST"]=cand[["_DIFF","_DIFF_FEE"]].min(axis=1)
        else:
            cand["_BEST"]=cand["_DIFF"]

        exact=cand[cand["_BEST"]<=float(tolerance)]
        sel=None; status="BANK RECEIPT PENDING"; rule=""; reason=""
        if len(exact)==1:
            sel=exact.iloc[0]; used.add(sel.name); status="BANK RECEIVED"
            if provider=="TABBY" and abs(float(sel["Bank Amount"])-(exp-tabby_fixed_fee))<=float(tolerance):
                rule=f"TABBY Payout - Fixed Fee SAR {tabby_fixed_fee:.2f} - Al Rajhi Credit"
            else:
                rule=f"{provider} Payout + Al Rajhi Credit"
        elif len(exact)>1:
            status="BANK REVIEW REQUIRED"; reason="Multiple provider bank receipts satisfy the payout"

        rec=r.to_dict()
        rec.update({
            "Settlement Status":status,
            "Bank Match Rule":rule,
            "Settlement Review Reason":reason,
            "Actual Bank Amount":float(sel["Bank Amount"]) if sel is not None else np.nan,
            "Bank Date":sel["Bank Date"] if sel is not None else pd.NaT,
            "Bank Difference":round(float(sel["Bank Amount"])-exp,2) if sel is not None else np.nan,
            "Bank Reference":sel["Description"] if sel is not None else "",
            "Bank Source File":sel["Bank Source File"] if sel is not None else "",
            # V27: same full-identity audit trail as the ANB card path.
            "Bank Source Sheet":sel.get("Bank Source Sheet","") if sel is not None else "",
            "Bank Source Row":sel.get("Bank Source Row","") if sel is not None else "",
        })
        rows.append(rec)

    result=pd.DataFrame(rows)
    return result,b[~b.index.isin(used)].copy()

def propagate_verified_batches(matched, batch_results):
    """
    Additive propagation. Uses Underlying IDs when present; otherwise applies
    exact ANB card batch identity Store + Terminal + POS Date + Payment.
    """
    if matched is None or matched.empty:
        return matched
    out=matched.copy()
    for c,default in [
        ("Settlement Batch ID",""),
        ("Settlement Stage","TRANSACTION MATCHED"),
        ("Provider Settled",False),
        ("Bank Settled",False),
        ("Settlement Match Rule",""),
        ("Settlement Bank Amount",np.nan),
        ("Settlement Bank Date",pd.NaT),
        ("Settlement Bank Reference",""),
        ("Settlement Evidence Source",""),
    ]:
        if c not in out.columns:
            out[c]=default

    if batch_results is None or batch_results.empty:
        return out

    for _,b in batch_results.iterrows():
        if str(b.get("Settlement Status",""))!="BANK RECEIVED":
            continue

        ids=[x for x in str(b.get("Underlying IDs","")).split("|") if x and x!="nan"]
        mask=pd.Series(False,index=out.index)

        if ids and "Unique Transaction ID" in out.columns:
            mask=out["Unique Transaction ID"].astype(str).isin(ids)
        else:
            provider=str(b.get("Provider","")).upper()
            if provider in {"ANB POS","AMEX"}:
                d=pd.to_datetime(out.get("POS Date",out.get("Date")),errors="coerce").dt.normalize()
                mask=(
                    out["Store Code"].astype(str).eq(str(b.get("Store Code","")))
                    & out["Payment Type"].apply(_norm_payment).eq(_norm_payment(b.get("Payment Type","")))
                    & d.eq(pd.to_datetime(b.get("Settlement Date"),errors="coerce").normalize())
                )
                if "Terminal ID" in out.columns and _txt(b.get("Terminal ID")):
                    mask &= out["Terminal ID"].astype(str).eq(_txt(b.get("Terminal ID")))

        if mask.any():
            out.loc[mask,"Settlement Batch ID"]=_txt(b.get("Settlement Batch ID"))
            out.loc[mask,"Settlement Stage"]="BANK RECEIVED"
            out.loc[mask,"Provider Settled"]=True
            out.loc[mask,"Bank Settled"]=True
            out.loc[mask,"Settlement Match Rule"]=_txt(b.get("Bank Match Rule"))
            out.loc[mask,"Settlement Bank Amount"]=b.get("Actual Bank Amount",np.nan)
            out.loc[mask,"Settlement Bank Date"]=b.get("Bank Date",pd.NaT)
            out.loc[mask,"Settlement Bank Reference"]=_txt(b.get("Bank Reference"))
            out.loc[mask,"Settlement Evidence Source"]=_txt(b.get("Bank Source File"))
    return out

def settlement_blocker_summary(matched):
    if matched is None or matched.empty:
        return pd.DataFrame()
    x=matched.copy()
    x["Bank Settled"]=x.get("Bank Settled",False).fillna(False).astype(bool)
    x["Settlement Stage"]=x.get("Settlement Stage","").fillna("").astype(str)
    rows=[]
    for (store,pay),g in x.groupby(["Store Code","Payment Type"],dropna=False):
        pending=g[~g["Bank Settled"]]
        rows.append({
            "Store Code":store,
            "Payment Type":pay,
            "Transactions":len(g),
            "Bank Settled":int(g["Bank Settled"].sum()),
            "Bank Pending":len(pending),
            "D365 Amount":float(pd.to_numeric(g.get("D365 Amount",0),errors="coerce").fillna(0).sum()),
            "Pending Amount":float(pd.to_numeric(pending.get("D365 Amount",0),errors="coerce").fillna(0).sum()) if not pending.empty else 0.0,
        })
    return pd.DataFrame(rows)

def engine_health():
    return {
        "module":"bank_settlement_extension",
        "legacy_preserved":True,
        "extension_mode":"additive parser + batch propagation",
    }


def reconcile_card_batches_advanced(batches, bank, tolerance=1.0):
    base,base_unmatched=reconcile_card_batches_to_anb(batches,bank,tolerance)
    if base is None or base.empty:
        return base,base_unmatched
    b=bank.copy() if bank is not None else pd.DataFrame()
    if b.empty:
        return base,base_unmatched
    anb=b[(b.get("Bank","").astype(str)=="ANB") & (pd.to_numeric(b.get("Credit",0),errors="coerce").fillna(0)>0)].copy()
    anb["_BankRowKey"]=anb.apply(_bank_row_key,axis=1)
    used=set()
    out=base.copy()

    # Reserve uniquely matched credits.
    # V27: reconcile_card_batches_to_anb() now carries the exact matched bank
    # row's Source File / Source Sheet / Source Row forward on the output
    # record (Actual Bank Amount / Bank Date are already carried). Recompute
    # the same deterministic key directly from those fields instead of
    # re-searching the bank pool by Description text, which could return zero
    # or multiple candidates when two credits share identical narration.
    for _,r in out[out["Settlement Status"].astype(str).eq("BANK RECEIVED")].iterrows():
        used.add(_bank_row_key({
            "Bank Source File":r.get("Bank Source File"),
            "Bank Source Sheet":r.get("Bank Source Sheet"),
            "Bank Source Row":r.get("Bank Source Row"),
            "Bank Date":r.get("Bank Date"),
            "Bank Amount":r.get("Actual Bank Amount"),
        }))

    for idx,r in out.iterrows():
        if str(r.get("Settlement Status",""))=="BANK RECEIVED":
            continue
        if str(r.get("Provider","")).upper() not in {"ANB POS","AMEX"}:
            continue

        terminal=_txt(r.get("Terminal ID"))
        pay=_norm_payment(r.get("Payment Type"))
        sdate=pd.to_datetime(r.get("Settlement Date"),errors="coerce")
        expected_net=float(pd.to_numeric(pd.Series([r.get("Expected Bank Amount",0)]),errors="coerce").fillna(0).iloc[0])
        gross=float(pd.to_numeric(pd.Series([r.get("Gross Amount",0)]),errors="coerce").fillna(0).iloc[0])
        batch_txc=pd.to_numeric(pd.Series([r.get("Transaction Count",np.nan)]),errors="coerce").iloc[0]

        cand=anb[~anb["_BankRowKey"].isin(used)].copy()
        if terminal:
            cand=cand[cand["Narration Terminal ID"].astype(str).eq(terminal)]
        if pay:
            cand=cand[cand["Narration Scheme"].apply(_norm_payment).eq(pay)]
        if pd.notna(sdate):
            cand=cand[pd.to_datetime(cand["Narration Source Date"],errors="coerce").dt.normalize().eq(sdate.normalize())]
        if cand.empty:
            continue

        bank_sum=float(pd.to_numeric(cand["Bank Amount"],errors="coerce").fillna(0).sum())
        fee_sum=float(pd.to_numeric(cand.get("Narration Fee",0),errors="coerce").fillna(0).sum())
        vat_sum=float(pd.to_numeric(cand.get("Narration VAT",0),errors="coerce").fillna(0).sum())
        tx_sum=float(pd.to_numeric(cand.get("Narration Transaction Count",0),errors="coerce").fillna(0).sum())

        if len(cand)>1 and abs(bank_sum-expected_net)<=float(tolerance):
            used.update(cand["_BankRowKey"].tolist())
            out.at[idx,"Settlement Status"]="BANK RECEIVED"
            out.at[idx,"Bank Match Rule"]="ANB Aggregate: Terminal + Source Date + Scheme + Net Amount"
            out.at[idx,"Settlement Review Reason"]=""
            out.at[idx,"Actual Bank Amount"]=bank_sum
            out.at[idx,"Bank Date"]=pd.to_datetime(cand["Bank Date"],errors="coerce").max()
            out.at[idx,"Bank Difference"]=round(bank_sum-expected_net,2)
            out.at[idx,"Bank Reference"]=" || ".join(cand["Description"].astype(str))
            out.at[idx,"Bank Source File"]=" | ".join(sorted(set(cand["Bank Source File"].astype(str))))
            continue

        gross_bridge=bank_sum+fee_sum+vat_sum
        count_ok=(pd.isna(batch_txc) or tx_sum==0 or abs(tx_sum-float(batch_txc))<0.001)
        if abs(gross_bridge-gross)<=float(tolerance) and count_ok:
            used.update(cand["_BankRowKey"].tolist())
            out.at[idx,"Settlement Status"]="BANK RECEIVED"
            out.at[idx,"Bank Match Rule"]="ANB Gross Proof: Bank Credit + Commission + VAT"
            out.at[idx,"Settlement Review Reason"]=""
            out.at[idx,"Actual Bank Amount"]=bank_sum
            out.at[idx,"Bank Date"]=pd.to_datetime(cand["Bank Date"],errors="coerce").max()
            out.at[idx,"Bank Difference"]=round(gross_bridge-gross,2)
            out.at[idx,"Bank Reference"]=" || ".join(cand["Description"].astype(str))
            out.at[idx,"Bank Source File"]=" | ".join(sorted(set(cand["Bank Source File"].astype(str))))
            continue

        out.at[idx,"Settlement Status"]="BANK REVIEW REQUIRED"
        out.at[idx,"Bank Match Rule"]="ANB Strong Identity - Amount Proof Failed"
        out.at[idx,"Settlement Review Reason"]=(
            f"{len(cand)} ANB credit(s) share Terminal/Date/Scheme. "
            f"Expected Net SAR {expected_net:,.2f}; Bank Total SAR {bank_sum:,.2f}; "
            f"Gross Proof SAR {gross_bridge:,.2f} vs Gross SAR {gross:,.2f}."
        )

    return out,anb[~anb["_BankRowKey"].isin(used)].drop(columns=["_BankRowKey"],errors="ignore").copy()
