from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.db.session import get_db
from app.schemas.documents import ChunkOut, DocumentOut
from app.services.document_service import delete_document, ingest_upload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))


@router.post("", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Document:
    return await ingest_upload(db, file)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if not document:
        from app.core.exceptions import RAGLabError

        raise RAGLabError("Document not found", status_code=404)
    return document


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_chunks(document_id: str, db: Session = Depends(get_db)) -> list[Chunk]:
    return list(
        db.scalars(
            select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index.asc()).limit(200)
        )
    )


@router.delete("/{document_id}")
def remove_document(document_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    delete_document(db, document_id)
    return {"status": "deleted", "document_id": document_id}

