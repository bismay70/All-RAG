from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    status: str
    size_bytes: int
    content_hash: str
    chunk_count: int
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    page: int | None = None
    section: str | None = None
    token_count: int

    model_config = {"from_attributes": True}

