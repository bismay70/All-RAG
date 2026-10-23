import json
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import RAGLabError
from app.db.models import Dataset, Experiment
from app.db.session import get_db
from app.evaluation.metrics import score_response
from app.schemas.chat import ChatRequest
from app.schemas.evaluation import DatasetCreate, DatasetOut, ExperimentCreate, ExperimentOut
from app.strategies.rag import run_rag

router = APIRouter(tags=["evaluation"])


@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetOut]:
    datasets = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    return [
        DatasetOut(id=item.id, name=item.name, description=item.description, items=json.loads(item.items_json))
        for item in datasets
    ]


@router.post("/datasets", response_model=DatasetOut)
def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)) -> DatasetOut:
    dataset = Dataset(id=str(uuid4()), name=payload.name, description=payload.description, items_json=payload.model_dump_json(include={"items"}))
    dataset.items_json = json.dumps([item.model_dump() for item in payload.items])
    db.add(dataset)
    db.commit()
    return DatasetOut(id=dataset.id, name=dataset.name, description=dataset.description, items=payload.items)


@router.post("/experiments", response_model=ExperimentOut)
async def run_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)) -> ExperimentOut:
    questions = payload.questions
    dataset_items = []
    if payload.dataset_id:
        dataset = db.get(Dataset, payload.dataset_id)
        if not dataset:
            raise RAGLabError("Dataset not found", status_code=404)
        dataset_items = json.loads(dataset.items_json)
        questions = [item["question"] for item in dataset_items]
    if not questions:
        raise RAGLabError("Provide questions or a dataset", status_code=400)

    results = []
    for strategy in payload.strategies[:5]:
        for index, question in enumerate(questions[:20]):
            response = await run_rag(db, ChatRequest(question=question, strategy=strategy, top_k=5))
            expected = dataset_items[index].get("expected_answer", "") if dataset_items else ""
            relevant = dataset_items[index].get("relevant_chunk_ids", []) if dataset_items else []
            results.append(
                {
                    "strategy": strategy,
                    "question": question,
                    "run_id": response.run_id,
                    "metrics": score_response(response, expected, relevant),
                }
            )
    experiment = Experiment(
        id=str(uuid4()),
        name=payload.name,
        dataset_id=payload.dataset_id,
        strategies_json=json.dumps(payload.strategies),
        results_json=json.dumps(results),
    )
    db.add(experiment)
    db.commit()
    return ExperimentOut(
        id=experiment.id,
        name=experiment.name,
        dataset_id=experiment.dataset_id,
        strategies=payload.strategies,
        results=results,
    )


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(db: Session = Depends(get_db)) -> list[ExperimentOut]:
    experiments = db.scalars(select(Experiment).order_by(Experiment.created_at.desc()).limit(50)).all()
    return [
        ExperimentOut(
            id=item.id,
            name=item.name,
            dataset_id=item.dataset_id,
            strategies=json.loads(item.strategies_json),
            results=json.loads(item.results_json),
        )
        for item in experiments
    ]

