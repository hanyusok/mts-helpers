import os
import time
import socket
import datetime
import logging
from typing import List, Optional, Union
from fastapi import HTTPException

import fdb

from config import (
    DB_HOST, DB_PORT, DB_DIR, DB_USER, DB_PASSWORD
)

logger = logging.getLogger("emr_db")

# Configure fdb charset mappings BEFORE establishing connections.
fdb.charset_map['NONE'] = 'cp949'
fdb.charset_map[None] = 'cp949'
fdb.charset_map['KSC_5601'] = 'cp949'

# Load the client library from the application root
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fb_dll_path = os.path.join(current_dir, "fbclient.dll")
if os.path.exists(fb_dll_path):
    try:
        fdb.load_api(fb_dll_path)
        logger.info(f"Successfully loaded Firebird client library from: {fb_dll_path}")
    except Exception as e:
        logger.error(f"Failed to load Firebird client library from {fb_dll_path}: {e}")

# Import decryptor if available
try:
    from decryptor import get_decryptor
    decrypt_client = get_decryptor()
except Exception as e:
    logger.debug(f"Optional decryptor not loaded: {e}")
    decrypt_client = None

def decrypt_pidnum(pidnum_enc: str) -> str:
    """Safely decrypts a patient's resident registration number if client is loaded."""
    if pidnum_enc and decrypt_client:
        try:
            return decrypt_client.decrypt(pidnum_enc)
        except Exception as e:
            logger.error(f"Failed to decrypt pidnum: {e}")
            return "DECRYPTION_ERROR"
    return pidnum_enc

def encrypt_pidnum(pidnum_plain: str) -> str:
    """Safely encrypts a patient's resident registration number into EMR Base64 ciphertext."""
    if pidnum_plain and decrypt_client:
        try:
            return decrypt_client.encrypt(pidnum_plain)
        except Exception as e:
            logger.error(f"Failed to encrypt pidnum: {e}")
            return ""
    return pidnum_plain

# Database Logging Wrappers
class LoggingCursor:
    def __init__(self, cursor, db_name: str):
        self._cursor = cursor
        self._db_name = db_name

    def execute(self, query, params=None):
        start_time = time.time()
        try:
            res = self._cursor.execute(query, params)
            duration = time.time() - start_time
            logger.debug(f"[{self._db_name}] Execute succeeded | Duration: {duration:.4f}s | Query: {query}")
            return res
        except Exception as e:
            logger.error(f"[{self._db_name}] Execute failed: {e} | Query: {query} | Params: {params}")
            raise

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    @property
    def description(self):
        return self._cursor.description

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class LoggingConnection:
    def __init__(self, connection, db_name: str):
        self._connection = connection
        self._db_name = db_name

    def cursor(self):
        return LoggingCursor(self._connection.cursor(), self._db_name)

    def commit(self):
        try:
            self._connection.commit()
            logger.debug(f"[{self._db_name}] Transaction committed.")
        except Exception as e:
            logger.error(f"[{self._db_name}] Commit failed: {e}")
            raise

    def rollback(self):
        try:
            self._connection.rollback()
            logger.warning(f"[{self._db_name}] Transaction rolled back.")
        except Exception as e:
            logger.error(f"[{self._db_name}] Rollback failed: {e}")
            raise

    def close(self):
        try:
            self._connection.close()
            logger.debug(f"[{self._db_name}] Connection closed.")
        except Exception as e:
            logger.error(f"[{self._db_name}] Close failed: {e}")
            raise

    def __getattr__(self, name):
        return getattr(self._connection, name)

_last_server_alive_check = {"time": 0.0, "alive": False}

def check_remote_server_alive(timeout: float = 1.0, max_cache_age: float = 3.0) -> bool:
    """Checks if the remote Firebird database server host/port is reachable, cached for 3 seconds."""
    if not DB_HOST or DB_HOST in ("127.0.0.1", "localhost"):
        return True
    now = time.time()
    if now - _last_server_alive_check["time"] < max_cache_age:
        return _last_server_alive_check["alive"]

    try:
        with socket.create_connection((DB_HOST, DB_PORT), timeout=timeout):
            _last_server_alive_check["time"] = now
            _last_server_alive_check["alive"] = True
            return True
    except Exception:
        _last_server_alive_check["time"] = now
        _last_server_alive_check["alive"] = False
        return False

def get_db_connection(db_name: str):
    db_path = os.path.join(DB_DIR, f"{db_name}.FDB")
    is_local = DB_HOST in ("127.0.0.1", "localhost", "", None)
    if is_local and not os.path.exists(db_path):
        logger.error(f"[DB CONNECTION ERROR] Database file not found locally: {db_path}")
        raise HTTPException(status_code=500, detail=f"Database file not found locally: {db_path}")
    
    # Fast check for remote server reachability to prevent long browser hangs
    if not is_local and not check_remote_server_alive(timeout=1.0):
        logger.warning(f"[DB CONNECTION] Remote host {DB_HOST}:{DB_PORT} is unreachable/stopped.")
        raise HTTPException(
            status_code=503,
            detail="현재 진료시간이 아니거나 진료준비중입니다. 진료시간에 접수해 주시기 바랍니다."
        )

    try:
        dsn = f"{DB_HOST}:{db_path}" if DB_HOST else db_path
        con = fdb.connect(
            dsn=dsn,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return LoggingConnection(con, db_name)
    except Exception as e:
        logger.error(f"[DB CONNECTION ERROR] Failed to connect to database {db_name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="현재 진료시간이 아니거나 진료준비중입니다. 진료시간에 접수해 주시기 바랍니다."
        )

_annual_tables_cache = {}
ANNUAL_TABLES_CACHE_TTL = 300.0  # 5 minutes cache

def get_annual_tables(db_name: str, prefix: str) -> List[str]:
    now = time.time()
    cache_key = (db_name.upper().strip(), prefix.upper().strip())
    if cache_key in _annual_tables_cache:
        cached_time, tables = _annual_tables_cache[cache_key]
        if now - cached_time < ANNUAL_TABLES_CACHE_TTL:
            return tables

    try:
        con = get_db_connection(db_name)
        cur = con.cursor()
        cur.execute("SELECT RDB$RELATION_NAME FROM RDB$RELATIONS WHERE RDB$SYSTEM_FLAG = 0")
        tables = [r[0].strip() for r in cur.fetchall()]
        con.close()
        
        annual_tables = []
        for t in tables:
            if t.startswith(prefix) and len(t) == len(prefix) + 4:
                year_part = t[len(prefix):]
                if year_part.isdigit():
                    annual_tables.append(t)
        result = sorted(annual_tables, reverse=True)
        _annual_tables_cache[cache_key] = (now, result)
        return result
    except Exception as e:
        logger.error(f"Error finding annual tables in {db_name} for prefix {prefix}: {e}")
        if cache_key in _annual_tables_cache:
            return _annual_tables_cache[cache_key][1]
        return []

def serialize_row(cols, vals):
    row_dict = {}
    for k, v in zip(cols, vals):
        if isinstance(v, (datetime.date, datetime.datetime)):
            row_dict[k.lower()] = v.isoformat()
        elif isinstance(v, datetime.time):
            row_dict[k.lower()] = v.strftime("%H:%M:%S")
        elif isinstance(v, str):
            row_dict[k.lower()] = v.strip()
        else:
            row_dict[k.lower()] = v
    return row_dict

def get_db(db_name: str):
    """Dependency generator for database connections."""
    def _get_db():
        con = get_db_connection(db_name)
        try:
            yield con
        finally:
            con.close()
    return _get_db

def calculate_age_str(
    birthdate: Union[datetime.date, datetime.datetime, str, None],
    ref_date: Optional[Union[datetime.date, datetime.datetime, str]] = None,
    as_korean: bool = False
) -> str:
    """
    Calculates patient age matching the legacy Firebird EMR (MTSMTR.AGE) format:
    - years >= 1:
        - months > 0: '{years}y {months}m ' (or Korean: '{years}년 {months}개월')
        - months == 0: '{years}y ' (or Korean: '{years}세')
    - years == 0:
        - months > 0:
            - days > 0: '{months}m {days}d' (or Korean: '{months}개월 {days}일')
            - days == 0: '{months}m ' (or Korean: '{months}개월')
        - months == 0:
            - '{days}d' (or Korean: '{days}일')
    """
    if not birthdate:
        return ""

    if isinstance(birthdate, datetime.datetime):
        birth = birthdate.date()
    elif isinstance(birthdate, datetime.date):
        birth = birthdate
    elif isinstance(birthdate, str):
        s = birthdate.strip()
        try:
            if "-" in s:
                birth = datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
            elif len(s) == 8 and s.isdigit():
                birth = datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            elif len(s) == 6 and s.isdigit():
                yy = int(s[:2])
                mm = int(s[2:4])
                dd = int(s[4:6])
                curr_yy = datetime.date.today().year % 100
                year = 2000 + yy if yy <= curr_yy else 1900 + yy
                birth = datetime.date(year, mm, dd)
            else:
                return ""
        except Exception:
            return ""
    else:
        return ""

    if ref_date is None:
        ref = datetime.date.today()
    elif isinstance(ref_date, datetime.datetime):
        ref = ref_date.date()
    elif isinstance(ref_date, datetime.date):
        ref = ref_date
    elif isinstance(ref_date, str):
        try:
            s_ref = ref_date.strip()
            if "-" in s_ref:
                ref = datetime.datetime.strptime(s_ref[:10], "%Y-%m-%d").date()
            elif len(s_ref) == 8 and s_ref.isdigit():
                ref = datetime.date(int(s_ref[:4]), int(s_ref[4:6]), int(s_ref[6:8]))
            else:
                ref = datetime.date.today()
        except Exception:
            ref = datetime.date.today()
    else:
        ref = datetime.date.today()

    years = ref.year - birth.year
    months = ref.month - birth.month
    days = ref.day - birth.day

    if days < 0:
        months -= 1
        prev_month_last_day = (ref.replace(day=1) - datetime.timedelta(days=1)).day
        days += prev_month_last_day

    if months < 0:
        years -= 1
        months += 12

    if as_korean:
        if years >= 1:
            if months > 0:
                return f"{years}년 {months}개월"
            else:
                return f"{years}세"
        else:
            if months > 0:
                if days > 0:
                    return f"{months}개월 {days}일"
                else:
                    return f"{months}개월"
            else:
                return f"{max(0, days)}일"

    # Standard Firebird EMR format
    if years >= 1:
        if months > 0:
            return f"{years}y {months}m "
        else:
            return f"{years}y "
    else:
        if months > 0:
            if days > 0:
                return f"{months}m {days}d"
            else:
                return f"{months}m "
        else:
            return f"{max(0, days)}d"

def calculate_korean_age_str(
    birthdate: Union[datetime.date, datetime.datetime, str, None],
    ref_date: Optional[Union[datetime.date, datetime.datetime, str]] = None
) -> str:
    """Calculates patient age as a detailed Korean display string."""
    return calculate_age_str(birthdate, ref_date=ref_date, as_korean=True)

def ensure_generator_exists(cur, generator_name: str) -> None:
    """Checks if a generator exists, and creates it if it does not."""
    gen_upper = generator_name.upper().strip()
    cur.execute("SELECT RDB$GENERATOR_NAME FROM RDB$GENERATORS WHERE TRIM(RDB$GENERATOR_NAME) = ?", (gen_upper,))
    gen_exists = cur.fetchone()
    if not gen_exists:
        cur.execute(f"CREATE GENERATOR {gen_upper}")
        cur.execute(f"SET GENERATOR {gen_upper} TO 0")
        logger.info(f"Dynamically created missing sequence generator: {gen_upper}")

def get_active_table(db_name: str, prefix: str) -> str:
    """Gets the table matching prefix + current year, creating it if missing."""
    current_year = datetime.date.today().year
    target_table = f"{prefix}{current_year}"
    
    tables = get_annual_tables(db_name, prefix)
    if target_table in tables:
        return target_table
        
    logger.warning(f"Active table {target_table} not found in {db_name}. Attempting dynamic initialization...")
    if not tables:
        raise RuntimeError(f"No legacy templates starting with {prefix} found in {db_name} to duplicate.")
    recent_table = tables[0]
    
    con = get_db_connection(db_name)
    cur = con.cursor()
    try:
        ensure_generator_exists(cur, f"GEN_{target_table}_SEQ")
        cur.execute(f"CREATE TABLE {target_table} AS SELECT * FROM {recent_table} WHERE 1=0")
        con.commit()
        logger.info(f"Successfully duplicated schema layout from {recent_table} to {target_table} in {db_name}")
        return target_table
    except Exception as e:
        con.rollback()
        logger.error(f"Failed to dynamically initialize table {target_table}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to dynamically initialize schema: {e}")
    finally:
        con.close()
