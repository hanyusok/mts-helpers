import datetime
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from config import get_clinic_info, get_active_doctors, find_doctor_by_key
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
    doc: Optional[str] = None
    room_code: Optional[int] = None
    doctor_name: Optional[str] = None

@router.get("/waiting")
def get_waiting(
    request: Request,
    source: str = Query("mtsmtr", description="Source database: 'mtswait' or 'mtsmtr' (default: mtsmtr)"),
    today: Optional[datetime.date] = None,
    limit: int = 50
):
    """Returns today's active waitlist with automatic privacy masking and multi-room grouping."""
    today = today or datetime.date.today()
    clean_source = source if isinstance(source, str) else "mtsmtr"
    clean_source = clean_source.lower().strip()
    clean_limit = limit if isinstance(limit, int) and not isinstance(limit, bool) else 50
    active_doctors = get_active_doctors()
    default_doc = active_doctors[0] if active_doctors else {"room_code": 1, "room_name": "제1진료실", "doctor_name": "김기중"}

    rooms_summary = {}
    for d in active_doctors:
        rc = str(d.get("room_code", 1))
        rooms_summary[rc] = {
            "room_code": d.get("room_code", 1),
            "room_name": d.get("room_name", f"제{rc}진료실"),
            "doctor_name": d.get("doctor_name", ""),
            "doctor_title": d.get("doctor_title", ""),
            "specialty": d.get("specialty", ""),
            "count": 0,
            "current_patient": None,
            "next_patient": None,
            "waiting_patients": []
        }

    try:
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
                raw_key = r.get("doc") or r.get("roomnm") or r.get("doctrnm")
                matched = find_doctor_by_key(raw_key) if raw_key else default_doc
                rc = str(matched.get("room_code", 1))
                r["room_code"] = matched.get("room_code", 1)
                r["room"] = matched.get("room_name", f"제{rc}진료실")
                r["doctor"] = matched.get("doctor_name", "")
                r["doctor_title"] = matched.get("doctor_title", "")
                r["specialty"] = matched.get("specialty", "")
                r["doc"] = str(matched.get("room_code", 1))
                r["pname"] = mask_korean_name(r.get("pname"))
                r["pidnum"] = None
                if r.get("patient"):
                    r["patient"]["pname"] = mask_korean_name(r["patient"].get("pname"))
                    r["patient"]["pidnum"] = None

                if rc in rooms_summary:
                    rooms_summary[rc]["count"] += 1
                    if rooms_summary[rc]["current_patient"] is None:
                        rooms_summary[rc]["current_patient"] = r.get("pname")
                    elif rooms_summary[rc]["next_patient"] is None:
                        rooms_summary[rc]["next_patient"] = r.get("pname")
                    else:
                        rooms_summary[rc]["waiting_patients"].append(r.get("pname"))

            return {
                "source": clean_source,
                "active_table": active_table,
                "queue": wait_records,
                "doctors": active_doctors,
                "rooms_summary": rooms_summary
            }

        # Default: MTSMTR
        mtr_records, active_table = QueueRepository.fetch_today_queue("MTSMTR", "MTR", today, clean_limit)
        for r in mtr_records:
            if r.get("pbirth"):
                r["age_korean"] = calculate_korean_age_str(r.get("pbirth"), ref_date=r.get("visidate"))
            raw_doc = str(r.get("doc", "") or "").strip()
            matched = find_doctor_by_key(raw_doc) if raw_doc else default_doc
            rc = str(matched.get("room_code", 1))
            r["room_code"] = matched.get("room_code", 1)
            r["room"] = matched.get("room_name", f"제{rc}진료실")
            r["doctor"] = matched.get("doctor_name", "")
            r["doctor_title"] = matched.get("doctor_title", "")
            r["specialty"] = matched.get("specialty", "")
            r["doc"] = str(matched.get("room_code", 1))
            r["pname"] = mask_korean_name(r.get("pname"))
            r["pidnum"] = None

            if rc in rooms_summary:
                rooms_summary[rc]["count"] += 1
                if rooms_summary[rc]["current_patient"] is None:
                    rooms_summary[rc]["current_patient"] = r.get("pname")
                elif rooms_summary[rc]["next_patient"] is None:
                    rooms_summary[rc]["next_patient"] = r.get("pname")
                else:
                    rooms_summary[rc]["waiting_patients"].append(r.get("pname"))

        return {
            "source": clean_source,
            "active_table": active_table,
            "queue": mtr_records,
            "doctors": active_doctors,
            "rooms_summary": rooms_summary
        }
    except Exception as e:
        logger.warning(f"Error fetching live queue ({clean_source}): {e}. Returning empty queue with room metadata.")
        return {
            "source": clean_source,
            "active_table": None,
            "queue": [],
            "doctors": active_doctors,
            "rooms_summary": rooms_summary,
            "warning": str(e)
        }

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
    """Create an MTSMTR ledger record (cloud/mobile/kiosk-initiated) with demographic verification and doctor selection."""
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

    # Determine assigned doctor/room
    active_docs = get_active_doctors()
    selected_key = req.doc or (str(req.room_code) if req.room_code else None) or req.doctor_name
    target_doc = find_doctor_by_key(selected_key) if selected_key else (active_docs[0] if active_docs else None)
    doc_val = str(target_doc.get("room_code", 1)) if target_doc else "1"

    return CheckinService.check_in_patient_pipeline(
        pcode=req.pcode,
        gubun=req.gubun or "모바일",
        background_tasks=background_tasks,
        con_mtr=con_mtr,
        doc=doc_val,
        target_doc=target_doc
    )
