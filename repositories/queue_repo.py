import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from database.firebird import get_active_table, ensure_generator_exists, serialize_row
from repositories.base import transaction_context

logger = logging.getLogger("queue_repo")

class QueueRepository:
    """Repository for managing waitlist and visit ledger records in MTSMTR and MTSWAIT."""

    @staticmethod
    def fetch_today_queue(
        db_name: str = "MTSMTR", 
        prefix: str = "MTR", 
        today: Optional[datetime.date] = None, 
        limit: int = 50,
        con=None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Fetches active waitlist/queue rows for today from the active annual table."""
        today = today or datetime.date.today()
        table_name = get_active_table(db_name, prefix)
        
        with transaction_context(db_name, con=con) as active_con:
            cur = active_con.cursor()
            if prefix == "WAIT":
                sql = f"SELECT FIRST {limit} * FROM {table_name} WHERE VISIDATE = ? ORDER BY RESID1 ASC"
            else:
                sql = f"SELECT FIRST {limit} * FROM {table_name} WHERE VISIDATE = ? AND (FIN IS NULL OR TRIM(FIN) <> '*') ORDER BY VISITIME ASC"
            cur.execute(sql, (today,))
            cols = [desc[0] for desc in cur.description]
            rows = [serialize_row(cols, r) for r in cur.fetchall()]
            
            # Inject resid1 / visitime keys into queue list rows
            if prefix == "MTR":
                for r in rows:
                    vd = r.get("visidate", "")
                    vt = r.get("visitime", "")
                    pcode = r.get("pcode", "")
                    if vd and vt and pcode is not None:
                        vd_clean = str(vd).replace("-", "")
                        vt_clean = str(vt).replace(":", "")[:4]
                        r["resid1"] = f"{vd_clean}{vt_clean}{pcode}"
            elif prefix == "WAIT":
                for r in rows:
                    resid1 = r.get("resid1", "")
                    if resid1 and len(resid1) >= 12:
                        hh = resid1[8:10]
                        mm = resid1[10:12]
                        r["visitime"] = f"{hh}:{mm}:00"
                    else:
                        r["visitime"] = ""
                        
            return rows, table_name

    @staticmethod
    def fetch_today_completed_queue(
        today: Optional[datetime.date] = None, 
        limit: int = 50,
        con=None
    ) -> List[Dict[str, Any]]:
        """Fetches completed treatment queue rows from MTSMTR where TRIM(FIN) = '*'."""
        today = today or datetime.date.today()
        table_name = get_active_table("MTSMTR", "MTR")
        
        with transaction_context("MTSMTR", con=con) as active_con:
            cur = active_con.cursor()
            sql = f"SELECT FIRST {limit} * FROM {table_name} WHERE VISIDATE = ? AND TRIM(FIN) = '*' ORDER BY VISITIME DESC"
            cur.execute(sql, (today,))
            cols = [desc[0] for desc in cur.description]
            rows = [serialize_row(cols, r) for r in cur.fetchall()]
            
            for r in rows:
                vd = r.get("visidate", "")
                vt = r.get("visitime", "")
                pcode = r.get("pcode", "")
                if vd and vt and pcode is not None:
                    vd_clean = str(vd).replace("-", "")
                    vt_clean = str(vt).replace(":", "")[:4]
                    r["resid1"] = f"{vd_clean}{vt_clean}{pcode}"
            return rows

    @staticmethod
    def insert_mtr_record(
        mtr_table: str,
        pcode: int,
        visidate: datetime.date,
        visitime: str,
        pname: str,
        sex: str,
        pbirth: Union[datetime.date, str],
        age_str: str,
        gubun: str = "모바일",
        doc: Optional[str] = None,
        fin: str = "",
        selfee: Optional[int] = None,
        genfee: Optional[int] = None,
        totalfee: Optional[int] = None,
        con=None
    ) -> int:
        """Inserts a new visit ledger record into the active annual MTSMTR table using its generator."""
        with transaction_context("MTSMTR", con=con) as active_con:
            cur = active_con.cursor()
            generator_name = f"GEN_{mtr_table}_SEQ"
            ensure_generator_exists(cur, generator_name)
            cur.execute(f"SELECT GEN_ID({generator_name}, 1) FROM RDB$DATABASE")
            next_id = cur.fetchone()[0]

            pbirth_val = pbirth.isoformat() if isinstance(pbirth, datetime.date) else str(pbirth)
            doc_val = doc[:4] if doc else None

            sql = f"""
                INSERT INTO {mtr_table} 
                ("#", PCODE, VISIDATE, VISITIME, PNAME, SEX, PBIRTH, AGE, FIN, SERIAL, GUBUN, DOC, SELFEE, GENFEE, TOTALFEE)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """
            cur.execute(sql, (
                next_id, pcode, visidate, visitime[:8], pname, sex[:1].upper(),
                pbirth_val, age_str, fin[:1], gubun[:4], doc_val, selfee, genfee, totalfee
            ))
            return next_id
