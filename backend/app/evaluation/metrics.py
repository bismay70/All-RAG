from app.schemas.chat import ChatResponse


def score_response(response: ChatResponse, expected_answer: str = "", relevant_chunk_ids: list[str] | None = None) -> dict[str, float | int | str]:
    relevant = set(relevant_chunk_ids or [])
    retrieved = [chunk.chunk_id for chunk in response.retrieved_chunks]
    hit_count = len([chunk_id for chunk_id in retrieved if chunk_id in relevant])
    recall = hit_count / len(relevant) if relevant else 0.0
    precision = hit_count / len(retrieved) if retrieved else 0.0
    expected_terms = set(expected_answer.lower().split())
    answer_terms = set(response.answer.lower().split())
    answer_overlap = len(expected_terms & answer_terms) / len(expected_terms) if expected_terms else 0.0
    return {
        "recall_at_k": round(recall, 4),
        "precision_at_k": round(precision, 4),
        "answer_term_overlap": round(answer_overlap, 4),
        "citation_count": len(response.citations),
        "verdict": response.verdict,
        "latency_ms": response.metrics.get("latency_ms", 0),
    }

