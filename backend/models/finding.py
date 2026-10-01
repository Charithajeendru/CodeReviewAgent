from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingLifecycle(str, Enum):
    DETECTED = "DETECTED"
    FIX_PROPOSED = "FIX_PROPOSED"
    FIX_VALIDATED = "FIX_VALIDATED"
    TEST_GENERATED = "TEST_GENERATED"
    REANALYZED = "REANALYZED"
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent: str
    severity: FindingSeverity
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    title: str
    description: str
    file: str = ""
    line_start: int | None = None
    line_end: int | None = None
    evidence: str = ""
    recommendation: str = ""
    lifecycle: list[FindingLifecycle] = Field(default_factory=lambda: [FindingLifecycle.DETECTED])


class FindingList(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
