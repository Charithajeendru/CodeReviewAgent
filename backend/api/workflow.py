from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.agents.fix_agent import generate_fix
from backend.agents.test_generation_agent import generate_finding_test
from backend.api.responses import success_response
from backend.database.database import db
from backend.models.workflow import FixResult, GenerateFixRequest, GenerateTestRequest, GeneratedTestResult, VerifyFixRequest
from backend.services.verification import verify_fix

router = APIRouter()


@router.post("/findings/{finding_id}/fix")
async def create_finding_fix(finding_id: uuid.UUID, payload: GenerateFixRequest) -> dict:
    if payload.finding.id != str(finding_id):
        raise HTTPException(status_code=400, detail="Finding ID does not match the request body.")
    result = await generate_fix(payload)
    serialized = result.model_dump(mode="json")
    db.save_fix(serialized)
    return success_response(db.get_fix(result.fix_id))


@router.get("/fixes/{fix_id}")
async def get_fix(fix_id: uuid.UUID) -> dict:
    result = db.get_fix(str(fix_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Fix not found.")
    return success_response(result)


@router.post("/fixes/{fix_id}/generate-test")
async def generate_fix_test(fix_id: uuid.UUID, payload: GenerateTestRequest | None = None) -> dict:
    fix = db.get_fix(str(fix_id))
    if fix is None:
        raise HTTPException(status_code=404, detail="Fix not found.")
    result = await generate_finding_test(
        FixResult.model_validate(fix),
        payload.framework if payload else None,
    )
    serialized = result.model_dump(mode="json")
    db.save_generated_test(serialized)
    return success_response(db.get_generated_test(result.test_id))


@router.post("/fixes/{fix_id}/verify")
async def verify_finding_fix(fix_id: uuid.UUID, payload: VerifyFixRequest | None = None) -> dict:
    fix = db.get_fix(str(fix_id))
    if fix is None:
        raise HTTPException(status_code=404, detail="Fix not found.")
    test = None
    test_id = str(payload.test_id) if payload and payload.test_id else None
    if test_id:
        test = db.get_generated_test(test_id)
        if test is None or test.get("fix_id") != str(fix_id):
            raise HTTPException(status_code=404, detail="Test not found for this fix.")

    result = verify_fix(
        FixResult.model_validate(fix),
        GeneratedTestResult.model_validate(test) if test else None,
    )
    serialized = result.model_dump(mode="json")
    db.save_verification(serialized)
    return success_response(db.get_verification(result.verification_id))


@router.get("/verifications/{verification_id}")
async def get_verification(verification_id: uuid.UUID) -> dict:
    result = db.get_verification(str(verification_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Verification result not found.")
    return success_response(result)
