import datetime
import logging
from typing import Any, Dict

from fastapi import BackgroundTasks, HTTPException

from database.firebird import calculate_age_str, calculate_korean_age_str, get_active_table, get_db_connection
from repositories.patient_repo import PatientRepository
from repositories.queue_repo import QueueRepository
from routers.websockets import customer_notifier

logger = logging.getLogger("checkin_service")

class CheckinService:
    """Business service for patient check-in workflows and queue updates."""

    @staticmethod
    def check_in_patient_pipeline(
        pcode: int,
        gubun: str,
        background_tasks: BackgroundTasks,
        con_mtr=None,
        doc: Optional[str] = None,
        target_doc: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes patient check-in pipeline (mobile or kiosk):
        1. Fetch patient demographics from MTSDB.PERSON
        2. Calculate accurate age string for Firebird DB
        3. Insert visit ledger record into active MTSMTR table with assigned doctor/room
        4. Broadcast WebSocket updates to /quicklist and /signage
        """
        con_db = get_db_connection("MTSDB")
        try:
            patient = PatientRepository.find_by_pcode(pcode, con=con_db)
            if not patient:
                raise HTTPException(status_code=404, detail=f"Patient with code {pcode} not found in PERSON table.")

            pname = patient["pname"]
            pbirth = patient["pbirth"]
            sex = patient["sex"]
            mtr_table = get_active_table("MTSMTR", "MTR")

            today = datetime.date.today()
            now_time = datetime.datetime.now().time()
            current_time_str = now_time.strftime("%H:%M:%S")

            resid1 = f"{today.strftime('%Y%m%d')}{now_time.strftime('%H%M')}{pcode}"
            age_str = calculate_age_str(pbirth, ref_date=today)
            age_korean = calculate_korean_age_str(pbirth, ref_date=today)

            # Insert into active MTSMTR table with doctor assignment
            next_id = QueueRepository.insert_mtr_record(
                mtr_table=mtr_table,
                pcode=pcode,
                visidate=today,
                visitime=current_time_str,
                pname=pname,
                sex=sex,
                pbirth=pbirth,
                age_str=age_str,
                gubun=gubun or "모바일",
                doc=doc,
                con=con_mtr
            )

            doc_name = target_doc.get("doctor_name", "") if target_doc else ""
            room_name = target_doc.get("room_name", "") if target_doc else ""
            room_code = target_doc.get("room_code", 1) if target_doc else 1

            # Broadcast queue update via WebSocket
            background_tasks.add_task(customer_notifier.broadcast, {
                "type": "QUEUE_UPDATE",
                "room_code": room_code,
                "timestamp": datetime.datetime.now().isoformat()
            })
            logger.info(f"Created ledger record in {mtr_table} with ID {next_id} for patient {pcode} ({pname}) -> {room_name} ({doc_name})")

            success_msg = f"{pname}님 접수가 완료되었습니다."
            if room_name and doc_name:
                success_msg = f"{pname}님 {room_name}({doc_name} 원장) 접수가 완료되었습니다."

            return {
                "status": "success",
                "message": success_msg,
                "mtr_id": next_id,
                "resid1": resid1,
                "pcode": pcode,
                "age": age_str,
                "age_korean": age_korean,
                "room_code": room_code,
                "room_name": room_name,
                "doctor_name": doc_name
            }
        finally:
            con_db.close()
