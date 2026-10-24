import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.retrieval.embeddings import EmbeddingProvider, cosine_similarity
from app.retrieval.lexical import lexical_scores


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    score: float
    dense_score: float
    lexical_score: float
    page: int | None = None
    section: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LocalRetrievalStore:
    def __init__(self, db: Session, embedder: EmbeddingProvider) -> None:
        self.db = db
        self.embedder = embedder

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        mode: str = "hybrid",
    ) -> list[SearchResult]:
        statement = select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
        if document_ids:
            statement = statement.where(Chunk.document_id.in_(document_ids))
        rows = self.db.execute(statement).all()
        if not rows:
            return []

        query_embedding = self.embedder.embed(query)
        dense: dict[str, float] = {}
        texts: dict[str, str] = {}
        row_map: dict[str, tuple[Chunk, Document]] = {}
        for chunk, document in rows:
            embedding = json.loads(chunk.embedding_json)
            dense[chunk.id] = max(0.0, cosine_similarity(query_embedding, embedding))
            texts[chunk.id] = chunk.text
            row_map[chunk.id] = (chunk, document)

        sparse = lexical_scores(query, texts)
        results: list[SearchResult] = []
        for chunk_id, (chunk, document) in row_map.items():
            dense_score = dense.get(chunk_id, 0.0)
            lexical_score = sparse.get(chunk_id, 0.0)
            if mode == "dense":
                score = dense_score
            elif mode == "lexical":
                score = lexical_score
            else:
                score = (0.62 * dense_score) + (0.38 * lexical_score)
            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    filename=document.filename,
                    text=chunk.text,
                    score=score,
                    dense_score=dense_score,
                    lexical_score=lexical_score,
                    page=chunk.page,
                    section=chunk.section,
                    metadata=json.loads(chunk.metadata_json or "{}"),
                )
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

