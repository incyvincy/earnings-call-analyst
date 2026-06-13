# Earnings Call Analyst

A domain-specific RAG system over public company earnings call transcripts. Ask
natural-language questions across quarters, track how management sentiment drifts
over time, and compare commentary across companies.

Not a generic "chat with PDF" demo. This uses metadata-aware retrieval,
cross-encoder reranking, FinBERT sentiment analysis, temporal drift tracking,
and a structured evaluation harness.

## Stack (100% free to run)

| Layer | Choice | Notes |
|-------|--------|-------|
| LLM | Google Gemini 2.5 Flash | Free tier via OpenAI-compatible API |
| Embeddings | `all-MiniLM-L6-v2` (SBERT) | Local, no API key needed |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Local cross-encoder |
| Sentiment | FinBERT-tone | Local HuggingFace model |
| Vector DB | ChromaDB | File-based, no Docker needed |
| Transcripts | Motley Fool scraper / local `.txt` files | Free public content |
| UI | Streamlit + Plotly | |

## Pipeline

```
ingest → process → embed → store → rag → app
(fetch)  (chunk +  (SBERT) (Chroma) (retrieve streamlit
         metadata)          + rerank  chat +
                            + LLM)    dashboards)
```

Each stage is an independent module under `src/`. Swap any backend in
`config.py` without touching the pipeline.

## Repo layout

```
earnings-call-analyst/
├── config.py                    # central settings, loaded from .env
├── requirements.txt
├── .env.example                 # copy to .env and fill keys
├── data/
│   └── transcripts/             # drop {TICKER}_{YEAR}_Q{N}.txt files here
├── src/
│   ├── ingest/
│   │   ├── transcripts.py       # LocalSource + MotleyFoolSource + FMPSource
│   │   ├── motleyfool.py        # free transcript scraper
│   │   └── edgar.py             # SEC EDGAR 8-K fallback
│   ├── process/
│   │   ├── chunker.py           # speaker- and section-aware chunking
│   │   └── metadata.py          # ticker, quarter, speaker, role labeling
│   ├── embed/
│   │   └── embedder.py          # local SBERT embeddings
│   ├── store/
│   │   └── vectorstore.py       # ChromaDB wrapper (upsert + filtered search)
│   ├── rag/
│   │   ├── prompts.py           # system + user prompt templates
│   │   ├── retriever.py         # vector search + cross-encoder rerank
│   │   └── engine.py            # retrieve → rerank → generate
│   ├── analysis/
│   │   ├── sentiment.py         # FinBERT temporal sentiment per quarter
│   │   └── compare.py           # cross-company commentary comparison
│   └── eval/
│       ├── benchmark.py         # QA benchmark loader/saver
│       └── metrics.py           # hit@k, faithfulness, answer relevance
├── app/
│   └── streamlit_app.py         # 3-tab UI: Ask / Sentiment / Compare
└── scripts/
    ├── build_index.py           # offline pipeline: fetch → chunk → embed → store
    ├── generate_samples.py      # generate sample transcripts via Gemini
    └── run_eval.py              # score against benchmark
```

## Quickstart

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Set up `.env`**
```bash
cp .env.example .env
# Fill in GEMINI_API_KEY (free at aistudio.google.com)
```

**3. Get transcripts**

Option A — generate sample transcripts with Gemini (instant, no scraping):
```bash
python scripts/generate_samples.py
```

Option B — drop your own `.txt` files into `data/transcripts/`:
```
data/transcripts/AAPL_2025_Q1.txt
data/transcripts/MSFT_2025_Q1.txt
```

Option C — auto-scrape from Motley Fool (set `TRANSCRIPT_SOURCE=motleyfool` in `.env`).

**4. Build the index**
```bash
set PYTHONPATH=.                  # Windows cmd
# or: export PYTHONPATH=.         # Mac/Linux

python scripts/build_index.py --tickers AAPL MSFT NVDA --quarters 2 --latest-year 2025 --latest-q 1
```

**5. Run the app**
```bash
streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501` with three tabs:
- **Ask** — grounded Q&A with citations (ticker + quarter)
- **Sentiment** — FinBERT sentiment drift chart per company/topic
- **Compare** — side-by-side answers from two companies

## What makes this non-trivial

- **Speaker-aware chunking** — chunks are attributed to CEO/CFO/analyst, enabling role-filtered retrieval
- **Cross-encoder reranking** — two-stage retrieval (vector recall → precision rerank) for better answers
- **Temporal metadata** — every chunk tagged with ticker, year, quarter, section so you can ask "what did the CFO say in Q3"
- **FinBERT sentiment** — finance-domain model scores prepared remarks per quarter, plotted as drift
- **Evaluation harness** — `run_eval.py` scores hit@k, faithfulness, and answer relevance

## Required API keys

| Key | Where to get | Free? |
|-----|-------------|-------|
| `GEMINI_API_KEY` | aistudio.google.com | Yes |
| `FMP_API_KEY` | financialmodelingprep.com | Yes (transcripts need paid plan) |

Only `GEMINI_API_KEY` is required to run the full pipeline.
