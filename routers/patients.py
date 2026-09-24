import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from services.patient_service import PatientService

logger = logging.getLogger("patients_router")

router = APIRouter()

class QuickVerifyRequest(BaseModel):
    pname: str
    birth: str
    resid2_first: Optional[str] = None

@router.post("/quick/verify")
def verify_quick_patient(req: QuickVerifyRequest):
    """
    Secure verification for mobile check-in.
    Verifies name and birthdate against PERSON table without leaking full lists or decrypted PIDNUMs.
    """
    if not req.pname.strip() or not req.birth.strip():
        return {
            "verified": False,
            "pcode": None,
            "message": "성명과 생년월일을 모두 입력해 주시기 바랍니다."
        }
    return PatientService.verify_quick_patient(req.pname, req.birth, req.resid2_first)
