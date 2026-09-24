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
        con_mtr=None
    ) -> Dict[str, Any]:
        """
        Executes patient mobile check-in pipeline:
        1. Fetch patient demographics from MTSDB.PERSON
        2. Calculate accurate age string for Firebird DB
        3. Insert visit ledger record into active MTSMTR table
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

            # Insert into active MTSMTR table
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
                con=con_mtr
            )

            # Broadcast queue update via WebSocket
            background_tasks.add_task(customer_notifier.broadcast, {
                "type": "QUEUE_UPDATE",
                "timestamp": datetime.datetime.now().isoformat()
            })
            logger.info(f"Created ledger record in {mtr_table} with ID {next_id} for patient {pcode} ({pname})")

            return {
                "status": "success",
                "message": f"{pname}님 접수가 완료되었습니다.",
                "mtr_id": next_id,
                "resid1": resid1,
                "pcode": pcode,
                "age": age_str,
                "age_korean": age_korean
            }
        finally:
            con_db.close()
