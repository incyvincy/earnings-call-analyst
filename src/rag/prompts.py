"""Prompt templates. Keep the model grounded and force citations so answers are
verifiable — this also makes faithfulness easy to measure in eval.
"""

SYSTEM = (
    "You are an equity research assistant. Answer ONLY from the provided "
    "earnings-call excerpts. If the excerpts do not contain the answer, say so "
    "plainly. Every claim must cite its source as [ticker Qx YEAR]. Be concise "
    "and precise with financial terminology."
)


def build_user_prompt(question: str, passages: list) -> str:
    blocks = []
    for i, p in enumerate(passages, 1):
        m = p.meta
        tag = f"{m.get('ticker')} Q{m.get('quarter')} {m.get('year')}"
        speaker = m.get("speaker") or "Unknown"
        blocks.append(f"[{i}] ({tag}, {speaker})\n{p.text}")
    context = "\n\n".join(blocks)
    return f"Question: {question}\n\nExcerpts:\n{context}\n\nAnswer with citations:"
