import hashlib
import json
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import RAGLabError
from app.db.models import Chunk, Document
from app.ingestion.chunkers import chunk_sections
from app.ingestion.parsers import parse_bytes
from app.retrieval.embeddings import HashEmbeddingProvider


async def ingest_upload(db: Session, upload: UploadFile) -> Document:
    settings = get_settings()
    content = await upload.read()
    if not content:
        raise RAGLabError("Uploaded file is empty", status_code=400)
    if len(content) > settings.upload_max_bytes:
        raise RAGLabError(
            "Uploaded file exceeds size limit",
            status_code=413,
            detail={"max_bytes": settings.upload_max_bytes},
        )

    content_hash = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(Document).where(Document.content_hash == content_hash))
    if existing:
        return existing

    document = Document(
        id=str(uuid4()),
        filename=upload.filename or "uploaded-file",
        content_type=upload.content_type or "application/octet-stream",
        status="processing",
        size_bytes=len(content),
        content_hash=content_hash,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        sections = parse_bytes(document.filename, content)
        chunks = chunk_sections(sections, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise RAGLabError("No readable text was found in the document", status_code=422)
        embedder = HashEmbeddingProvider(settings.embedding_dimensions)
        for index, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            db.add(
                Chunk(
                    id=str(uuid4()),
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk.text,
                    page=chunk.page,
                    section=chunk.section,
                    token_count=chunk.token_count,
                    content_hash=chunk_hash,
                    embedding_json=json.dumps(embedder.embed(chunk.text)),
                    metadata_json=json.dumps({"embedding_model": embedder.name}),
                )
            )
        document.status = "indexed"
        document.chunk_count = len(chunks)
        document.error = None
    except Exception as exc:
        document.status = "failed"
        document.error = str(exc)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document_id: str) -> None:
    document = db.get(Document, document_id)
    if not document:
        raise RAGLabError("Document not found", status_code=404)
    db.delete(document)
    db.commit()

