from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str
    document_id: str
    filename: str
    page: int | None = None
    section: str | None = None
    chunk_id: str
    quote: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    text: str
    score: float
    dense_score: float | None = None
    lexical_score: float | None = None
    page: int | None = None
    section: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceEvent(BaseModel):
    node: str
    status: str = "ok"
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: float | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    database: str
    grok_configured: bool
    langsmith_configured: bool
    configured_secret_names: list[str]
    checked_at: datetime

