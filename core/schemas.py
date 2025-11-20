from typing import List, Dict, Optional
from pydantic import BaseModel


class AnswerRequest(BaseModel):
    answer: str


class DialogResponse(BaseModel):
    phase: str
    state: str
    question: str
    tree: List[Dict]
    ose_results: List[Dict] = []
    message: Optional[str] = None
