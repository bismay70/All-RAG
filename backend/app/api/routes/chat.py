from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, PipelineInfo
from app.strategies.catalog import PIPELINES
from app.strategies.rag import run_rag

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return await run_rag(db, request)


@router.get("/pipelines", response_model=list[PipelineInfo])
def list_pipelines() -> list[PipelineInfo]:
    return PIPELINES

