import datetime
import logging
import re
from typing import Any, Dict, Optional

from repositories.patient_repo import PatientRepository

logger = logging.getLogger("patient_service")

class PatientService:
    """Business service for patient verification in quick mobile check-in."""

    @staticmethod
    def verify_quick_patient(pname: str, birth: str, resid2_first: Optional[str] = None) -> Dict[str, Any]:
        """
        Secure patient verification for mobile check-in.
        Matches name and birthdate against MTSDB.PERSON without leaking full PIDNUM.
        """
        clean_name = pname.strip()
        clean_birth = re.sub(r"[^\d]", "", birth.strip())
        
        candidates = PatientRepository.find_by_name(clean_name)
        if not candidates:
            return {
                "verified": False,
                "pcode": None,
                "message": "등록된 환자 정보를 찾을 수 없습니다. 처음 오신 분은 접수처 데스크에 문의해 주세요."
            }

        for candidate in candidates:
            pcode = candidate["pcode"]
            db_pbirth = candidate.get("pbirth")
            
            db_birth_clean = ""
            if isinstance(db_pbirth, (datetime.date, datetime.datetime)):
                db_birth_clean = db_pbirth.strftime("%Y%m%d")
            elif db_pbirth:
                db_birth_clean = re.sub(r"[^\d]", "", str(db_pbirth))

            is_match = False
            if db_birth_clean == clean_birth:
                is_match = True
            elif len(clean_birth) == 8 and len(db_birth_clean) == 8 and clean_birth == db_birth_clean:
                is_match = True
            elif len(clean_birth) == 6 and len(db_birth_clean) >= 8 and db_birth_clean[2:8] == clean_birth:
                is_match = True
            elif len(clean_birth) == 8 and len(db_birth_clean) == 6 and clean_birth[2:8] == db_birth_clean:
                is_match = True

            if is_match:
                # Mask Korean name for privacy
                s = clean_name
                masked_name = s[0] + "*" * (len(s) - 2) + s[-1] if len(s) >= 3 else (s[0] + "*" if len(s) == 2 else s)
                return {
                    "verified": True,
                    "pcode": pcode,
                    "pname": masked_name,
                    "message": "환자 정보가 확인되었습니다."
                }

        return {
            "verified": False,
            "pcode": None,
            "message": "등록된 환자 정보를 찾을 수 없습니다. 처음 오신 분은 접수처 데스크에 문의해 주세요."
        }
