from pydantic import BaseModel, Field
from typing import List, Literal, Tuple

class ExtractedEntity(BaseModel):
    skill_id: str = Field(..., description="Canonical UUID from DB")
    canonical_name: str = Field(..., description="Display name, e.g. 'Apache Spark'")
    verbatim_text: str = Field(..., description="What was actually found, e.g. 'Spark'")
    span: Tuple[int, int] = Field(..., description="(start_char, end_char) indices in source text")
    confidence: float = Field(..., ge=0.0, le=1.0)
    match_method: Literal["exact_dictionary", "fuzzy_vector", "alias"]

class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity]
    processed_text_length: int
    processing_time_ms: float
