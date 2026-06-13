"""Streamlit demo UI: chat with sources, sentiment drift, cross-company compare.

    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.analysis.compare import compare
from src.analysis.sentiment import sentiment_by_quarter
from src.rag.engine import ask

st.set_page_config(page_title="Earnings Call Analyst", layout="wide")
st.title("Earnings Call Analyst")

tab_chat, tab_sentiment, tab_compare = st.tabs(["Ask", "Sentiment drift", "Compare"])

with tab_chat:
    ticker = st.text_input("Ticker filter (optional)", "").strip().upper()
    q = st.text_input("Ask a question about the earnings calls")
    if st.button("Ask") and q:
        where = {"ticker": ticker} if ticker else None
        ans = ask(q, where=where)
        st.markdown(ans.text)
        with st.expander(f"Sources ({len(ans.passages)})"):
            for p in ans.passages:
                m = p.meta
                st.caption(f"{m['ticker']} Q{m['quarter']} {m['year']} — {m.get('speaker')}")
                st.write(p.text)

with tab_sentiment:
    t = st.text_input("Ticker", "AAPL", key="sent_ticker").strip().upper()
    topic = st.text_input("Topic (optional, e.g. China, margins)", "").strip()
    if st.button("Plot drift") and t:
        series = sentiment_by_quarter(t, topic or None)
        if series:
            periods = list(series.keys())
            vals = [series[p] for p in periods]
            fig = go.Figure(go.Scatter(x=periods, y=vals, mode="lines+markers"))
            fig.update_layout(yaxis_title="sentiment (+pos / -neg)", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data — build the index for this ticker first.")

with tab_compare:
    c1, c2 = st.columns(2)
    a = c1.text_input("Company A", "MSFT").strip().upper()
    b = c2.text_input("Company B", "GOOGL").strip().upper()
    cq = st.text_input("Question to compare", "What did they say about AI capex?")
    if st.button("Compare") and a and b and cq:
        res = compare(cq, a, b)
        left, right = st.columns(2)
        for col, tk in ((left, a), (right, b)):
            col.subheader(tk)
            col.markdown(res[tk].text)
