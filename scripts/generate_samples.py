"""Generate realistic sample earnings call transcripts using Groq.

Uses publicly known Q1 2025 financial results to produce transcripts that
are accurate enough to demonstrate the RAG pipeline. Saves to data/transcripts/
so the local source can index them immediately.

Usage:
    python scripts/generate_samples.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from config import settings

TRANSCRIPTS_DIR = Path("data/transcripts")
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=settings.gemini_api_key, base_url=settings.gemini_base_url)

COMPANIES = [
    {
        "ticker": "AAPL",
        "year": 2025,
        "quarter": 1,
        "context": """Apple Q1 FY2025 (quarter ended December 28, 2024), reported January 30, 2025.
CEO: Tim Cook. CFO: Kevan Parekh (new CFO replacing Luca Maestri).
Key results: Revenue $124.3B (record, +4% YoY). iPhone revenue $69.1B (+1%).
Mac $9.0B (+16%). iPad $8.1B (+15%). Wearables $11.7B (-2%).
Services $26.3B (record, +14%). Gross margin 46.9% (record).
EPS $2.40. Cash returned to shareholders: $30B.
Key themes: Apple Intelligence AI features, strong Services growth,
iPhone 16 cycle, China revenue $18.5B (-11%), India growth strong.""",
    },
    {
        "ticker": "MSFT",
        "year": 2025,
        "quarter": 1,
        "context": """Microsoft Q2 FY2025 (quarter ended December 31, 2024), reported January 29, 2025.
CEO: Satya Nadella. CFO: Amy Hood.
Key results: Revenue $69.6B (+12% YoY). Cloud revenue $40.9B (+21%).
Azure and other cloud services +31% (including ~13pts from AI services).
Office Commercial products +15%. Dynamics +14%. LinkedIn +9%.
More Personal Computing $14.7B (+3%). Gaming +5%.
Operating income $31.7B (+17%). EPS $3.23 (+10%).
Key themes: Microsoft Copilot adoption across 365, Azure AI capacity expansion,
$80B planned AI infrastructure spend in FY2025, GitHub Copilot surpassing
15M users, strong enterprise AI demand outpacing supply.""",
    },
    {
        "ticker": "NVDA",
        "year": 2025,
        "quarter": 1,
        "context": """NVIDIA Q3 FY2025 (quarter ended October 27, 2024), reported November 20, 2024.
CEO: Jensen Huang. CFO: Colette Kress.
Key results: Revenue $35.1B (+94% YoY, +17% QoQ). Record quarter.
Data Center revenue $30.8B (+112% YoY). Gaming $3.3B (+15%).
Professional Visualization $486M (+17%). Automotive $449M (+72%).
Gross margin 74.6%. Operating income $21.9B. EPS $0.81 (adjusted $0.81).
Blackwell GPU production ramping, demand exceeds supply.
Key themes: Blackwell architecture ramp, sovereign AI, inference demand,
CUDA ecosystem moat, next-gen Rubin platform announced for 2026,
hyperscaler capex boom driving sustained demand.""",
    },
    {
        "ticker": "AAPL",
        "year": 2024,
        "quarter": 4,
        "context": """Apple Q4 FY2024 (quarter ended September 28, 2024), reported October 31, 2024.
CEO: Tim Cook. CFO: Luca Maestri (final quarter before Kevan Parekh took over).
Key results: Revenue $94.9B (+6% YoY). iPhone revenue $46.2B (+6%).
Mac $7.7B (+2%). iPad $7.0B (+8%). Wearables $9.0B (-3%).
Services $24.2B (+12%). Gross margin 46.2%. EPS $1.64.
Key themes: iPhone 16 launched with Apple Intelligence, iOS 18 rollout,
China pressure continuing, India as growth market, Vision Pro momentum.""",
    },
    {
        "ticker": "MSFT",
        "year": 2024,
        "quarter": 4,
        "context": """Microsoft Q1 FY2025 (quarter ended September 30, 2024), reported October 30, 2024.
CEO: Satya Nadella. CFO: Amy Hood.
Key results: Revenue $65.6B (+16% YoY). Cloud $38.9B (+22%).
Azure +33% including ~12pts from AI. Office Commercial +15%.
Operating income $30.6B (+14%). EPS $3.30 (+10%).
Key themes: Copilot Studio, Azure AI scaling, OpenAI partnership deepening,
Microsoft 365 Copilot enterprise traction, data center buildout.""",
    },
    {
        "ticker": "NVDA",
        "year": 2024,
        "quarter": 4,
        "context": """NVIDIA Q2 FY2025 (quarter ended July 28, 2024), reported August 28, 2024.
CEO: Jensen Huang. CFO: Colette Kress.
Key results: Revenue $30.0B (+122% YoY, +15% QoQ). Record quarter.
Data Center $26.3B (+154% YoY). Gaming $2.9B (+9%).
Gross margin 75.1%. EPS $0.68 (adjusted). Hopper still dominant.
Blackwell production beginning, H200 strong demand.
Key themes: AI infrastructure supercycle, CUDA installed base,
inference workloads growing, supply chain improving.""",
    },
]

PROMPT_TEMPLATE = """You are transcribing an earnings call. Generate a realistic, detailed earnings call transcript based on the actual financial results below. Include:
1. Operator introduction
2. IR director opening (2-3 sentences)
3. CEO prepared remarks (400-500 words) covering business highlights, product updates, and strategic priorities
4. CFO prepared remarks (300-400 words) covering detailed financial results, segment breakdown, and guidance
5. Q&A section with 4-5 analyst questions and detailed management answers (each exchange 150-200 words)

Use realistic analyst names (e.g., Amit Daryanani from Evercore, Ben Reitzes from Melius, Wamsi Mohan from BofA, Erik Woodring from Morgan Stanley, Shannon Cross from Credit Suisse).
Use the exact financial figures provided. Write in the authentic voice of each executive.

Financial context:
{context}

Write the complete transcript now:"""


def generate(company: dict) -> None:
    ticker = company["ticker"]
    year = company["year"]
    quarter = company["quarter"]
    path = TRANSCRIPTS_DIR / f"{ticker}_{year}_Q{quarter}.txt"

    if path.exists():
        print(f"  {path.name} already exists — skipping.")
        return

    print(f"  Generating {path.name}...")
    resp = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.7,
        max_tokens=3000,
        messages=[
            {"role": "user", "content": PROMPT_TEMPLATE.format(context=company["context"])},
        ],
    )
    text = resp.choices[0].message.content
    path.write_text(text, encoding="utf-8")
    print(f"  Saved {len(text):,} chars → {path}")


if __name__ == "__main__":
    print(f"Generating {len(COMPANIES)} sample transcripts with Groq...\n")
    for company in COMPANIES:
        generate(company)
    print("\nDone! Now run:")
    print("  python scripts/build_index.py --tickers AAPL MSFT NVDA --quarters 2 --latest-year 2025 --latest-q 1")
