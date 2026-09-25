import logging
from typing import Any, Dict, List, Optional

from database.firebird import serialize_row
from repositories.base import transaction_context

logger = logging.getLogger("patient_repo")

class PatientRepository:
    """Repository for managing patient lookups in MTSDB."""

    @staticmethod
    def find_by_pcode(pcode: int, con=None) -> Optional[Dict[str, Any]]:
        """Finds patient demographic info by PCODE from MTSDB.PERSON."""
        with transaction_context("MTSDB", con=con) as active_con:
            cur = active_con.cursor()
            cur.execute("SELECT PCODE, PNAME, PBIRTH, SEX, PIDNUM, FCODE, LASTCHECK FROM PERSON WHERE PCODE = ?", (pcode,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [desc[0] for desc in cur.description]
            return serialize_row(cols, row)

    @staticmethod
    def find_by_name(pname: str, con=None) -> List[Dict[str, Any]]:
        """Finds candidate patients by exact name from MTSDB.PERSON for quick verification."""
        with transaction_context("MTSDB", con=con) as active_con:
            cur = active_con.cursor()
            cur.execute("SELECT PCODE, PNAME, PBIRTH, SEX, PIDNUM FROM PERSON WHERE PNAME = ?", (pname.strip(),))
            cols = [desc[0] for desc in cur.description]
            return [serialize_row(cols, r) for r in cur.fetchall()]

    @staticmethod
    def search_patients(
        pname: Optional[str] = None, 
        pcode: Optional[int] = None, 
        limit: int = 50, 
        con=None
    ) -> List[Dict[str, Any]]:
        """Searches patients by name or exact code from MTSDB.PERSON."""
        clean_pname = str(pname).strip() if isinstance(pname, str) and str(pname).strip() else None
        clean_pcode = pcode if isinstance(pcode, int) and not isinstance(pcode, bool) else None
        clean_limit = limit if isinstance(limit, int) and not isinstance(limit, bool) else 50

        with transaction_context("MTSDB", con=con) as active_con:
            cur = active_con.cursor()
            sql = f"SELECT FIRST {clean_limit} PCODE, PNAME, PBIRTH, PIDNUM, SEX, LASTCHECK FROM PERSON"
            params = []
            conditions = []
            
            if clean_pcode is not None:
                conditions.append("PCODE = ?")
                params.append(clean_pcode)
            if clean_pname:
                conditions.append("PNAME LIKE ?")
                params.append(f"%{clean_pname}%")
                
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY PCODE DESC"
            
            cur.execute(sql, tuple(params))
            cols = [desc[0] for desc in cur.description]
            return [serialize_row(cols, r) for r in cur.fetchall()]

