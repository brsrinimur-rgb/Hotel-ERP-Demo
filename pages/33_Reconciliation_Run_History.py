import streamlit as st
import pandas as pd
import auth, theme
from logic import run_history

st.set_page_config(page_title="Reconciliation Run History",layout="wide",page_icon="🗂️")
auth.require_login({"Admin","Finance Manager","Finance Maker","Finance Checker"})
auth.render_user_sidebar()
st.markdown(theme.global_css(),unsafe_allow_html=True)
st.markdown(theme.top_banner("RETAIL CONTROL TOWER","Reconciliation Run History"),unsafe_allow_html=True)

st.title("🗂️ Reconciliation Run History")
st.caption(
    "Every successful RUN RECONCILIATION creates a new, permanent Run ID. Running a new "
    "reconciliation never overwrites an older run - it only ever adds one. Use this page to "
    "prove what any past reconciliation looked like at the time it was run, or to reopen an "
    "older run as the active working session."
)

current_run_id=st.session_state.get("current_run_id")
st.metric("Current Run",current_run_id or "None yet - run POS Reconciliation first")

runs=run_history.list_runs()
if runs.empty:
    st.info("No reconciliation runs have been saved yet. Run POS Reconciliation to create the first one.")
    st.stop()

st.markdown("### Load Previous Run")

def _label(row):
    return (
        f"{row['run_id']} · {row['created_at'][:16].replace('T',' ')} · "
        f"{row['user_name'] or row['username'] or 'Unknown user'} · "
        f"Matched {int(row['matched_count'])} · Bank Settled {int(row['bank_settled_count'])}"
    )

runs["_label"]=runs.apply(_label,axis=1)
selected_label=st.selectbox("Select a run to view",runs["_label"].tolist())
selected_run_id=runs.loc[runs["_label"]==selected_label,"run_id"].iloc[0]
meta=run_history.get_run_meta(selected_run_id)

m1,m2,m3,m4=st.columns(4)
m1.metric("Run ID",meta.get("run_id",""))
m2.metric("Created",str(meta.get("created_at",""))[:19].replace("T"," "))
m3.metric("Run By",meta.get("user_name") or meta.get("username") or "Unknown")
m4.metric("Period",f"{str(meta.get('period_from',''))[:10]} → {str(meta.get('period_to',''))[:10]}")

m5,m6,m7=st.columns(3)
m5.metric("Matched",int(meta.get("matched_count") or 0))
m6.metric("Unmatched D365 / POS",f"{int(meta.get('unmatched_sales_count') or 0)} / {int(meta.get('unmatched_pos_count') or 0)}")
m7.metric("Bank Settled",int(meta.get("bank_settled_count") or 0))

snapshot=run_history.load_run(selected_run_id)

st.markdown("### Saved Reports for This Run")
tab_defs=[
    ("Matched","matched"),
    ("Unmatched D365","unmatched_sales"),
    ("Unmatched POS","unmatched_pos"),
    ("Settlement Batches","settlement_batches"),
    ("Settlement Bank Unmatched","settlement_bank_unmatched"),
    ("Provider Payout Batches","provider_payout_batches"),
    ("Bank","bank"),
    ("Quarantine","quarantine"),
    ("Carry Forward","carry_forward"),
]
available=[(label,key) for label,key in tab_defs if key in snapshot and not snapshot[key].empty]
if not available:
    st.info("This run has no saved report data (it may predate Run History, or the run produced no rows).")
else:
    tabs=st.tabs([label for label,_ in available])
    for tab,(label,key) in zip(tabs,available):
        with tab:
            st.dataframe(snapshot[key],use_container_width=True,hide_index=True)

st.divider()
st.markdown("### Reopen as Current Working Session")
st.caption(
    "This replaces the data every other page reads from st.session_state (Settlement Batch "
    "Engine, Exception Correction Center, JV Creation, etc.) with this saved run. Your actual "
    "current working session, if different, is auto-saved under its own Run ID first, so "
    "nothing is lost - it just stops being 'Current Run' until you reopen it here again."
)
confirm=st.checkbox(f"I understand this will make {selected_run_id} the Current Run")
if st.button("REOPEN THIS RUN",type="primary",disabled=not confirm or selected_run_id==current_run_id):
    live=st.session_state.get("ct_result")
    if current_run_id and live:
        try:
            run_history.save_run(current_run_id,live,created_at=pd.Timestamp.today().isoformat())
        except Exception:
            pass
    st.session_state.ct_result=snapshot
    st.session_state["current_run_id"]=selected_run_id
    st.success(f"{selected_run_id} is now the Current Run.")
    st.rerun()
