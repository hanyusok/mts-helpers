import datetime
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from config import get_clinic_info
from database.firebird import calculate_korean_age_str, get_db
from repositories.patient_repo import PatientRepository
from repositories.queue_repo import QueueRepository
from routers.common import mask_korean_name
from services.checkin_service import CheckinService

logger = logging.getLogger("queue_router")

router = APIRouter()

class CloudMtrCreate(BaseModel):
    pcode: int
    pname: Optional[str] = None
    pbirth: Optional[datetime.date] = None
    gubun: str = "모바일"

@router.get("/waiting")
def get_waiting(
    request: Request,
    source: str = Query("mtsmtr", description="Source database: 'mtswait' or 'mtsmtr' (default: mtsmtr)"),
    today: Optional[datetime.date] = None,
    limit: int = 50
):
    """Returns today's active waitlist with automatic privacy masking."""
    today = today or datetime.date.today()
    clean_source = source if isinstance(source, str) else "mtsmtr"
    clean_source = clean_source.lower().strip()
    clean_limit = limit if isinstance(limit, int) and not isinstance(limit, bool) else 50
    clinic_cfg = get_clinic_info()
    default_doctor = clinic_cfg.get("doctor_name", "김기중")
    default_room = clinic_cfg.get("room_name", "제1진료실")

    if clean_source == "mtswait":
        wait_records, active_table = QueueRepository.fetch_today_queue("MTSWAIT", "WAIT", today, clean_limit)
        for r in wait_records:
            pcode = r.get("pcode")
            if pcode is not None:
                patient = PatientRepository.find_by_pcode(pcode)
                r["patient"] = patient
                if patient:
                    r["pname"] = patient.get("pname")
                    r["sex"] = patient.get("sex")
                    r["pbirth"] = patient.get("pbirth")
            r["room"] = r.get("roomnm") or default_room
            r["doctor"] = r.get("doctrnm") or default_doctor
            r["pname"] = mask_korean_name(r.get("pname"))
            r["pidnum"] = None
            if r.get("patient"):
                r["patient"]["pname"] = mask_korean_name(r["patient"].get("pname"))
                r["patient"]["pidnum"] = None
        return {"source": clean_source, "active_table": active_table, "queue": wait_records}

    # Default: MTSMTR
    mtr_records, active_table = QueueRepository.fetch_today_queue("MTSMTR", "MTR", today, clean_limit)
    for r in mtr_records:
        if r.get("pbirth"):
            r["age_korean"] = calculate_korean_age_str(r.get("pbirth"), ref_date=r.get("visidate"))
        r["pname"] = mask_korean_name(r.get("pname"))
        r["pidnum"] = None
        r["room"] = default_room
        r["doctor"] = default_doctor
    return {"source": clean_source, "active_table": active_table, "queue": mtr_records}

@router.get("/waiting/completed")
def get_waiting_completed(today: Optional[datetime.date] = None, limit: int = 50):
    """Returns today's completed treatment records."""
    today = today or datetime.date.today()
    records = QueueRepository.fetch_today_completed_queue(today, limit)
    for r in records:
        r["pname"] = mask_korean_name(r.get("pname"))
        r["pidnum"] = None
    return {"status": "success", "count": len(records), "completed": records}

@router.post("/mtr")
def create_mtr_cloud(req: CloudMtrCreate, background_tasks: BackgroundTasks, con_mtr=Depends(get_db("MTSMTR"))):
    """Create an MTSMTR ledger record (cloud/mobile-initiated) with demographic verification."""
    patient = PatientRepository.find_by_pcode(req.pcode)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {req.pcode} not found")

    if req.pname and req.pname.strip() != patient["pname"].strip():
        raise HTTPException(status_code=400, detail="입력하신 성명이 EMR 데이터베이스 정보와 일치하지 않습니다.")
        
    if req.pbirth:
        db_pbirth = patient["pbirth"]
        if isinstance(db_pbirth, (datetime.date, datetime.datetime)):
            db_pbirth_date = db_pbirth if isinstance(db_pbirth, datetime.date) else db_pbirth.date()
        else:
            try:
                db_pbirth_date = datetime.datetime.strptime(str(db_pbirth).strip(), "%Y-%m-%d").date()
            except ValueError:
                db_pbirth_date = None
        if db_pbirth_date and req.pbirth != db_pbirth_date:
            raise HTTPException(status_code=400, detail="입력하신 생년월일이 EMR 데이터베이스 정보와 일치하지 않습니다.")

    return CheckinService.check_in_patient_pipeline(
        pcode=req.pcode,
        gubun=req.gubun or "모바일",
        background_tasks=background_tasks,
        con_mtr=con_mtr
    )
