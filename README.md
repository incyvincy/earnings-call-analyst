# Earnings Call Analyst

A domain-specific RAG system over public company earnings call transcripts. Ask
natural-language questions across quarters, track how management sentiment drifts
over time, and compare commentary across companies.

This is the part recruiters care about: it's not "upload a PDF and chat." It's
metadata-aware retrieval, financial-domain embeddings, reranking, temporal
analysis, and a real evaluation harness.

## Pipeline

```
ingest  ->  process  ->  embed  ->  store  ->  rag  ->  app
(fetch)     (chunk +     (FinBERT/  (Qdrant)   (retrieve  (Streamlit
            metadata)    OpenAI)               + rerank   chat +
                                               + LLM)     dashboards)
```

Each stage is a module under `src/`. The two scripts in `scripts/` wire them
together: `build_index.py` runs the offline ingest pipeline, `run_eval.py` scores
the system against a benchmark.

## Repo layout

```
earnings-call-analyst/
├── README.md
├── requirements.txt
├── .env.example            # copy to .env and fill keys
├── config.py               # central settings, loaded from env
├── data/                   # raw + processed transcripts (gitignored)
├── src/
│   ├── ingest/
│   │   ├── edgar.py         # SEC EDGAR 8-K exhibits (prepared remarks)
│   │   └── transcripts.py   # transcript API (FMP / API Ninjas) abstraction
│   ├── process/
│   │   ├── chunker.py       # speaker- and section-aware chunking
│   │   └── metadata.py      # ticker, quarter, fiscal date, speaker, role
│   ├── embed/
│   │   └── embedder.py      # pluggable embedding backend
│   ├── store/
│   │   └── vectorstore.py   # Qdrant wrapper (upsert + filtered search)
│   ├── rag/
│   │   ├── prompts.py       # system + answer prompt templates
│   │   ├── retriever.py     # vector search + cross-encoder rerank
│   │   └── engine.py        # orchestrates retrieve -> rerank -> generate
│   ├── analysis/
│   │   ├── sentiment.py     # FinBERT sentiment over quarters
│   │   └── compare.py       # cross-company commentary diff
│   └── eval/
│       ├── benchmark.py     # build/load the QA eval set
│       └── metrics.py       # retrieval acc, faithfulness, answer relevance
├── app/
│   └── streamlit_app.py     # the demo UI
├── scripts/
│   ├── build_index.py       # end-to-end: fetch -> chunk -> embed -> store
│   └── run_eval.py          # run the benchmark, print metrics
└── tests/
    └── test_pipeline.py
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in your keys

# start a local Qdrant (docker) or point at Qdrant Cloud
docker run -p 6333:6333 qdrant/qdrant

# build the index for a few tickers
python scripts/build_index.py --tickers AAPL MSFT NVDA --quarters 8

# run the app
streamlit run app/streamlit_app.py
```

## Build plan

Day 1 — data + index
- Wire one transcript source end to end (`transcripts.py`). Get 8 quarters for
  3–4 tickers into `data/`.
- Speaker/section-aware chunking + metadata extraction.
- Embed and upsert into Qdrant with metadata payloads (ticker, quarter, speaker,
  section). Filtered search working.

Day 2 — RAG + UI
- Retriever with metadata filters + cross-encoder rerank.
- RAG engine: retrieve -> rerank -> grounded answer with citations.
- Streamlit chat that shows the answer plus the source passages it used.

Day 3 — the differentiators (this is the resume gold)
- Temporal sentiment: FinBERT over each quarter's prepared remarks, plotted as a
  drift line per topic.
- Cross-company compare: same question against two tickers, side by side.

Day 4 — evaluation (do not skip)
- Build ~150–200 QA pairs (seed them from sell-side report summaries or generate
  + hand-verify).
- Score retrieval accuracy (hit@k), faithfulness (answer grounded in retrieved
  context), and answer relevance. This number on your resume is what closes it.

## Notes
- Transcripts proper (with Q&A) live on Motley Fool / Seeking Alpha / paid APIs.
  EDGAR 8-K exhibits often contain only prepared remarks — good free fallback.
  Check each provider's terms before scraping.
- Swap the embedding/LLM backends in `config.py` without touching the pipeline.
