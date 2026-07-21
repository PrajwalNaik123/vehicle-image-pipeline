from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    id: str
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatusResponse(BaseModel):
    id: str
    status: str
    failure_reason: Optional[str] = None
    uploaded_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckResult(BaseModel):
    check_name: str
    passed: bool
    confidence: float
    detail: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResultsResponse(BaseModel):
    id: str
    status: str
    failure_reason: Optional[str] = None
    results: List[CheckResult]

    model_config = ConfigDict(from_attributes=True)
