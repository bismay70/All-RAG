from typing import Any

from pydantic import BaseModel, Field


class DatasetItem(BaseModel):
    question: str
    expected_answer: str = ""
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    answerable: bool = True
    tags: list[str] = Field(default_factory=list)


class DatasetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = ""
    items: list[DatasetItem] = Field(default_factory=list)


class DatasetOut(DatasetCreate):
    id: str


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    dataset_id: str | None = None
    questions: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=lambda: ["simple", "hybrid", "corrective"])


class ExperimentOut(BaseModel):
    id: str
    name: str
    dataset_id: str | None
    strategies: list[str]
    results: list[dict[str, Any]]

