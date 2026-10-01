from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.models.finding import Finding


class AgentResult(BaseModel):
    agent: str
    status: Literal["ok", "warning", "error", "unavailable"] = "ok"
    message: str = ""
    findings: list[Finding] = Field(default_factory=list)
