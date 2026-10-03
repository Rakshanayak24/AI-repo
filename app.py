from __future__ import annotations

import json
import html
from dataclasses import asdict

import streamlit as st

from worker import INBOX, LEDGER, InvoiceTools, run_task

st.set_page_config(page_title="CentrAlign · Operator", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--bg:#090e16;--panel:#101824;--line:#1d2a38;--muted:#8190a3;--text:#e9f0f7;--mint:#71e0bc;--amber:#f1bd72;}
.stApp{background:radial-gradient(ellipse at 75% 0%,#132431 0%,#090e16 44%);color:var(--text);font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"]{right:1rem}
.block-container{max-width:1180px;padding-top:2.2rem;padding-bottom:4rem}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.035em;color:var(--text)}
.topline{display:flex;align-items:center;gap:10px;color:#afbdcc;font:500 12px 'DM Mono',monospace;letter-spacing:.12em;text-transform:uppercase;margin-bottom:28px}
.mark{width:28px;height:28px;border-radius:9px;background:linear-gradient(135deg,#8ef4d1,#34b994);display:grid;place-items:center;color:#071711;font-weight:800;font-size:16px;box-shadow:0 0 28px #51dbb533}
.eyebrow{font:500 11px 'DM Mono',monospace;letter-spacing:.15em;text-transform:uppercase;color:var(--mint)}
.hero{font:700 42px/1.12 'Manrope',sans-serif;letter-spacing:-.055em;margin:10px 0 12px;color:#f0f6fc}
.sub{color:#91a0b0;font-size:15px;line-height:1.65;max-width:660px}
.panel{background:linear-gradient(145deg,#111c29e8,#0e1621e8);border:1px solid var(--line);border-radius:16px;padding:21px 23px;margin-bottom:14px;box-shadow:0 12px 40px #00000017}
[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(145deg,#111c29e8,#0e1621e8);border:1px solid var(--line);border-radius:16px;padding:4px 16px;box-shadow:0 12px 40px #00000017;margin-bottom:14px}
.panel-title{font:600 12px 'DM Mono',monospace;letter-spacing:.11em;text-transform:uppercase;color:#a9b9c9;margin-bottom:15px}
.metric-label{color:#8291a2;font:500 10px 'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase}
.metric-value{color:#ecf3fa;font:600 19px 'Manrope',sans-serif;margin-top:6px}
.metric-note{color:#8190a3;font-size:12px;margin-top:3px}
.stTextArea textarea{background:#0b131d!important;color:#e9f0f7!important;border:1px solid #293949!important;border-radius:11px!important;font-size:14px!important}
.stButton>button{background:#75e2bd!important;color:#082017!important;border:0!important;border-radius:9px!important;padding:.58rem 1.15rem!important;font-weight:700!important;box-shadow:0 5px 20px #4ad8ae26}
.stButton>button:hover{background:#9cf2d4!important;transform:translateY(-1px)}
.event{display:grid;grid-template-columns:78px 1fr;gap:12px;padding:13px 0;border-bottom:1px solid #1a2632}
.event:last-child{border:0}.event-time{font:11px 'DM Mono',monospace;color:#708094;padding-top:3px}.event-stage{font:600 12px 'DM Mono',monospace;color:#78dcb9}.event-message{font-size:13px;color:#d6e0e9;margin-top:3px}.event-detail{font-size:12px;color:#8796a7;margin-top:4px;line-height:1.5;overflow-wrap:anywhere}
.pill{display:inline-flex;border:1px solid #285545;background:#10271f;color:#84e7c2;padding:5px 9px;border-radius:30px;font:11px 'DM Mono',monospace;letter-spacing:.04em}
.foot{color:#667587;font:11px 'DM Mono',monospace;border-top:1px solid #1b2733;padding-top:16px;margin-top:28px}
div[data-testid="stExpander"]{background:#101824;border:1px solid #1d2a38;border-radius:12px}
</style>
""", unsafe_allow_html=True)

def panel_title(title: str):
    st.markdown(f'<div class="panel-title">{title}</div>', unsafe_allow_html=True)

st.markdown('<div class="topline"><span class="mark">◈</span> CENTRALIGN <span style="color:#516173">/</span> OPERATOR LAB <span class="pill" style="margin-left:auto">LOCAL SANDBOX</span></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">AUTONOMOUS WORKER · PROTOTYPE 01</div><div class="hero">From invoice to<br>verified work.</div><div class="sub">Give the operator an outcome. It finds the right document, extracts what matters, navigates the approval policy, writes to the finance ledger and checks its work.</div>', unsafe_allow_html=True)
st.write("")

files = InvoiceTools().list_invoices()
rows = InvoiceTools().read_ledger()
columns = st.columns(4)
metrics = [("INBOX", str(len(files)), "local invoice PDFs"), ("AP LEDGER", str(len(rows)), "verified records"), ("EXECUTION", "Tool-driven", "observe · adapt · verify"), ("GUARDRAIL", "₹100k", "approval threshold")]
for col, (label, value, note) in zip(columns, metrics):
    with col:
        st.markdown(f'<div class="panel" style="padding:16px 18px"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

left, right = st.columns([1.08, .92], gap="large")
with left:
    with st.container(border=True):
        panel_title("01 / Define the outcome")
        goal = st.text_area("Task", value="Process the latest invoice from Northstar Components: extract the amount and due date, enter it in accounts payable, then confirm when it is done.", height=112, label_visibility="collapsed")
        a, b = st.columns([1, 1])
        with a:
            inject_failure = st.toggle("Simulate one connector timeout", value=True, help="Demonstrates bounded retry and recovery.")
        with b:
            approve = st.toggle("Approve high-value invoice", value=False, help="Invoices at or above ₹100,000 require explicit approval.")
        run = st.button("Run operator  →", type="primary", use_container_width=True)

    with st.container(border=True):
        panel_title("02 / Company context")
        st.markdown('<div style="font-size:13px;color:#bfccd8;line-height:1.8">▸ Inbox: <code>data/inbox/</code><br>▸ System of record: local AP ledger<br>▸ Policy: invoices ≥ ₹100,000 need human approval<br>▸ Duplicate key: invoice number<br>▸ Retry budget: one retry for transient failures</div>', unsafe_allow_html=True)

with right:
    with st.container(border=True):
        panel_title("03 / Execution trace")
        if run:
            result = run_task(goal, fail_once=inject_failure, approve=approve)
            st.session_state["last_run"] = result
        result = st.session_state.get("last_run")
        if result:
            if result["status"] == "complete": st.markdown('<span class="pill">● VERIFIED COMPLETE</span>', unsafe_allow_html=True)
            elif result["status"] == "needs_approval": st.markdown('<span class="pill" style="border-color:#685132;background:#2a2114;color:#f1bd72">◉ AWAITING APPROVAL</span>', unsafe_allow_html=True)
            else: st.markdown('<span class="pill" style="border-color:#6c343a;background:#2c171b;color:#ff9d9d">● NEEDS ATTENTION</span>', unsafe_allow_html=True)
            st.write("")
            for event in result["events"]:
                color = "#f1bd72" if event.status in ("warning", "approval") else "#ff9090" if event.status == "error" else "#78dcb9"
                safe_time, safe_stage = html.escape(event.timestamp), html.escape(event.stage.upper())
                safe_message, safe_detail = html.escape(event.message), html.escape(event.detail)
                st.markdown(f'<div class="event"><div class="event-time">{safe_time}</div><div><div class="event-stage" style="color:{color}">{safe_stage}</div><div class="event-message">{safe_message}</div><div class="event-detail">{safe_detail}</div></div></div>', unsafe_allow_html=True)
            safe_summary = html.escape(result["summary"])
            st.markdown(f'<div style="margin-top:16px;padding:13px 15px;border-radius:10px;background:#0b131d;border:1px solid #202e3b;color:#c8d6e2;font-size:13px;line-height:1.6">{safe_summary}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#8594a5;font-size:13px;line-height:1.8;padding:18px 0">The worker will expose every decision and tool result here. Run the sample task to inspect the full goal → plan → execute → verify loop.</div>', unsafe_allow_html=True)

with st.expander("Inspect the local accounts payable ledger"):
    ledger = InvoiceTools().read_ledger()
    if ledger:
        st.dataframe(ledger, use_container_width=True, hide_index=True)
    else:
        st.caption("No invoices recorded yet. A verified run will create the first ledger entry.")

with st.expander("Available sample invoices"):
    for path in InvoiceTools().list_invoices():
        st.markdown(f"`{path.name}`")

st.markdown('<div class="foot">CENTRALIGN AI · ENGINEERING HIRING EXERCISE · ALL DATA IS LOCAL AND SYNTHETIC</div>', unsafe_allow_html=True)
