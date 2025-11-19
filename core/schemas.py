from pydantic import BaseModel
from typing import List, Dict


class AnswerRequest(BaseModel):
    answer: str


class DialogResponse(BaseModel):
    phase: str
    state: str
    question: str
    tree: List[Dict]
    ose_results: List[Dict] = []
    message: str | None = None
