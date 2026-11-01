from pydantic import BaseModel
from typing import Dict, List, Optional

ACTION_LABELS = [
    "Patient Instructions",
    "Appointment",
    "Medication",
    "Lab",
    "Procedure",
    "Imaging",
    "Other",
]

class Span(BaseModel):
    start: int
    end: int
    label: str
    text: Optional[str] = None
    confidence: Optional[float] = None
    raw_labels: Optional[List[str]] = None

class ExtractRequest(BaseModel):
    text: str

class ExtractResponse(BaseModel):
    spans: List[Span]


class InferRequest(BaseModel):
    text: str


class SentencePrediction(BaseModel):
    sentence: str
    labels: List[str]
    confidences: Dict[str, float]


class InferResponse(BaseModel):
    sentences: List[SentencePrediction]
    grouped_items: Dict[str, List[str]]
    spans: List[Span]