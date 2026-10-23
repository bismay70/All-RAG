import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import RAGLabError
from app.db.models import Run
from app.db.session import get_db

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("")
def list_traces(db: Session = Depends(get_db)) -> list[dict]:
    runs = db.scalars(select(Run).order_by(Run.created_at.desc()).limit(50)).all()
    return [
        {
            "id": run.id,
            "question": run.question,
            "strategy": run.strategy,
            "verdict": run.verdict,
            "metrics": json.loads(run.metrics_json),
            "created_at": run.created_at,
        }
        for run in runs
    ]


@router.get("/{run_id}")
def get_trace(run_id: str, db: Session = Depends(get_db)) -> dict:
    run = db.get(Run, run_id)
    if not run:
        raise RAGLabError("Run not found", status_code=404)
    return {
        "id": run.id,
        "question": run.question,
        "strategy": run.strategy,
        "answer": run.answer,
        "verdict": run.verdict,
        "metrics": json.loads(run.metrics_json),
        "trace": json.loads(run.trace_json),
        "citations": json.loads(run.citations_json),
        "usage": json.loads(run.usage_json),
        "created_at": run.created_at,
    }

