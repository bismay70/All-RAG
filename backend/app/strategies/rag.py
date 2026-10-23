import json
import re
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Run
from app.generation.citations import build_citations
from app.generation.providers import XAIProvider
from app.observability.local_tracing import LocalTrace
from app.retrieval.embeddings import HashEmbeddingProvider
from app.retrieval.store import LocalRetrievalStore, SearchResult
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import RetrievedChunk


QUESTION_WORDS = {"what", "why", "how", "when", "where", "who", "which"}


async def run_rag(db: Session, request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    trace = LocalTrace()
    started = time.perf_counter()
    embedder = HashEmbeddingProvider(settings.embedding_dimensions)
    store = LocalRetrievalStore(db, embedder)
    provider = XAIProvider(settings)
    warnings: list[str] = []

    strategy = _resolve_strategy(request.strategy, request.question)
    top_k = request.top_k
    mode = "dense" if strategy in {"simple", "two_step"} else "hybrid"
    trace.add("classify_query", message=f"Selected {strategy}", metadata={"requested_strategy": request.strategy})

    with trace.node("retrieve_dense_sparse", mode=mode, top_k=top_k):
        retrieved = store.search(request.question, top_k=top_k, document_ids=request.document_ids, mode=mode)

    if strategy in {"multi_query", "query_decomposition", "hyde", "contextual"}:
        with trace.node("transform_query", strategy=strategy):
            variants = _query_variants(request.question, strategy)
        retrieved = _merge_results(retrieved, [store.search(variant, top_k=top_k, document_ids=request.document_ids) for variant in variants])
        trace.add("fuse_results", metadata={"variant_count": len(variants), "candidate_count": len(retrieved)})

    if strategy in {"reranked", "hybrid", "corrective", "adaptive", "parent", "compression", "sentence_window"}:
        with trace.node("rerank_results", strategy=strategy):
            retrieved = _rerank(request.question, retrieved)

    if strategy == "corrective" and (not retrieved or retrieved[0].score < 0.12):
        trace.add("grade_retrieval", status="weak", message="Evidence below threshold; rewriting once.")
        rewritten = _rewrite_query(request.question)
        with trace.node("rewrite_query", rewritten=rewritten):
            retry_results = store.search(rewritten, top_k=top_k, document_ids=request.document_ids, mode="hybrid")
        retrieved = _rerank(request.question, _merge_results(retrieved, [retry_results]))
    else:
        trace.add("grade_retrieval", message="Evidence accepted" if retrieved else "No evidence found")

    if strategy in {"parent", "sentence_window"}:
        trace.add("expand_context", message="Neighbor expansion is approximated by returning same-document evidence.")

    selected = retrieved[:top_k]
    generation = await provider.generate(request.question, selected)
    warnings.extend(generation.warnings)
    trace.add("generate_answer", metadata={"provider": generation.provider, "warning_count": len(generation.warnings)})

    citations = build_citations(selected)
    verdict = "insufficient_evidence" if not selected or selected[0].score < 0.05 else "grounded"
    if "not have enough indexed evidence" in generation.answer.lower():
        verdict = "insufficient_evidence"
    trace.add("verify_citations", metadata={"citation_count": len(citations), "verdict": verdict})

    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics = {
        "latency_ms": round(elapsed_ms, 2),
        "retrieved": len(selected),
        "top_score": round(selected[0].score, 4) if selected else 0,
        "strategy_status": "implemented" if strategy in {"simple", "two_step", "hybrid", "corrective"} else "experimental",
    }
    usage = {"provider": generation.provider, **generation.usage}
    run_id = str(uuid4())
    response = ChatResponse(
        run_id=run_id,
        strategy=strategy,
        answer=generation.answer,
        citations=citations,
        retrieved_chunks=[
            RetrievedChunk(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                filename=item.filename,
                text=item.text,
                score=item.score,
                dense_score=item.dense_score,
                lexical_score=item.lexical_score,
                page=item.page,
                section=item.section,
                metadata=item.metadata,
            )
            for item in selected
        ],
        verdict=verdict,
        metrics=metrics,
        trace=trace.events,
        usage=usage,
        warnings=warnings,
    )
    db.add(
        Run(
            id=run_id,
            question=request.question,
            strategy=strategy,
            answer=response.answer,
            verdict=response.verdict,
            metrics_json=json.dumps(metrics),
            trace_json=json.dumps([event.model_dump() for event in response.trace]),
            citations_json=json.dumps([citation.model_dump() for citation in citations]),
            usage_json=json.dumps(usage),
        )
    )
    db.commit()
    return response


def _resolve_strategy(strategy: str, question: str) -> str:
    if strategy == "adaptive":
        terms = question.lower().split()
        if len(terms) > 18 or {"compare", "contrast", "why", "how"}.intersection(terms):
            return "corrective"
        return "hybrid"
    return strategy


def _query_variants(question: str, strategy: str) -> list[str]:
    clean = question.strip()
    if strategy == "query_decomposition":
        parts = re.split(r"\band\b|\bthen\b|;|,", clean, flags=re.IGNORECASE)
        return [part.strip(" ?") for part in parts if len(part.strip()) > 8][:3]
    if strategy == "hyde":
        return [f"An answer to this question would mention: {clean}"]
    if strategy == "contextual":
        return [clean, f"document section explaining {clean}"]
    return [clean, " ".join(word for word in clean.split() if word.lower() not in QUESTION_WORDS)]


def _rewrite_query(question: str) -> str:
    return " ".join(word for word in question.replace("?", "").split() if word.lower() not in QUESTION_WORDS)


def _merge_results(primary: list[SearchResult], groups: list[list[SearchResult]]) -> list[SearchResult]:
    merged: dict[str, SearchResult] = {item.chunk_id: item for item in primary}
    for group in groups:
        for item in group:
            if item.chunk_id not in merged or item.score > merged[item.chunk_id].score:
                merged[item.chunk_id] = item
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)


def _rerank(question: str, results: list[SearchResult]) -> list[SearchResult]:
    question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    for result in results:
        result_terms = set(re.findall(r"[a-z0-9]+", result.text.lower()))
        overlap = len(question_terms & result_terms) / max(len(question_terms), 1)
        result.score = min(1.0, (result.score * 0.8) + (overlap * 0.2))
    return sorted(results, key=lambda item: item.score, reverse=True)

