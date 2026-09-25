import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from repositories.patient_repo import PatientRepository
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

@router.get("/patients")
def get_patients(
    pname: Optional[str] = Query(None, description="Filter by Patient Name"),
    pcode: Optional[int] = Query(None, description="Filter by exact Patient Code"),
    limit: int = Query(50, description="Limit records returned")
):
    """Queries MTSDB.PERSON table for kiosk and desk lookup."""
    try:
        clean_pname = pname if isinstance(pname, str) else None
        clean_pcode = pcode if isinstance(pcode, int) and not isinstance(pcode, bool) else None
        clean_limit = limit if isinstance(limit, int) and not isinstance(limit, bool) else 50
        rows = PatientRepository.search_patients(pname=clean_pname, pcode=clean_pcode, limit=clean_limit)
        results = []
        for r in rows:
            # Mask PIDNUM for privacy safety
            if hasattr(r.get("pbirth"), "strftime"):
                r["pbirth"] = r["pbirth"].strftime("%Y-%m-%d")
            r["pidnum"] = None
            results.append(r)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))
