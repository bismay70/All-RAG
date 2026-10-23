from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import Citation, RetrievedChunk, TraceEvent


StrategyId = Literal[
    "simple",
    "two_step",
    "hybrid",
    "reranked",
    "multi_query",
    "query_decomposition",
    "parent",
    "compression",
    "sentence_window",
    "hyde",
    "contextual",
    "corrective",
    "self_rag",
    "adaptive",
    "iterative",
    "multihop",
    "structured",
    "temporal",
    "federated",
    "graph",
    "raptor",
    "multimodal",
    "agentic",
    "multi_agent",
    "flare",
    "replug",
    "late_chunking",
]


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    strategy: StrategyId = "hybrid"
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    run_id: str
    strategy: str
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
    verdict: str
    metrics: dict[str, Any]
    trace: list[TraceEvent]
    usage: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class PipelineInfo(BaseModel):
    id: str
    name: str
    status: Literal["implemented", "experimental", "planned"]
    description: str
    uses_langgraph: bool = False

