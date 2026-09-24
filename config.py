import os
import json
import logging

logger = logging.getLogger("config")

# Server Configurations
HOST = os.getenv("EMR_GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("EMR_GATEWAY_PORT", "3010"))

# Remote Firebird Database Configuration
DB_HOST = os.getenv("EMR_DB_HOST", "192.168.0.12")  # EMR Doctor PC IP (e.g. DAVID)
DB_PORT = int(os.getenv("EMR_DB_PORT", "3050"))
DB_DIR = os.getenv("EMR_DB_DIR", "C:/mts3/db")
DB_USER = os.getenv("EMR_DB_USER", "SYSDBA")
DB_PASSWORD = os.getenv("EMR_DB_PASSWORD", "masterkey")

# Decryption Subprocess Settings
DECRYPT_WORKER_NAME = "DecryptWorker.exe"

# Data file for dynamic clinic info
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLINIC_INFO_FILE = os.path.join(DATA_DIR, "clinic_info.json")

# Default Clinic Profile
DEFAULT_CLINIC_INFO = {
    "clinic_name": "김기중 소아청소년과의원",
    "clinic_name_en": "KIM KI JOONG PEDIATRICS",
    "clinic_insucode": "41334655",
    "doctor_name": "김기중",
    "doctor_title": "김기중 원장",
    "specialty": "소아청소년과 전문의",
    "dept_code": "11",
    "dept_name": "소아청소년과",
    "room_code": 1,
    "room_name": "제1진료실",
    "doctor_code": "63221",
    "address": "경기 수원시 팔달구 (매교역 2번 출구)",
    "directions": "수인분당선 매교역 2번 출구 바로 앞",
    "map_url": "https://naver.me/GgUzsloE",
    "phone": "031-234-5678",
    "open_time": "10:00",
    "close_time": "18:00",
    "lunch_start": "12:00",
    "lunch_end": "13:30",
    "weekend_open": True,
    "closed_weekdays": [1, 2],
    "closed_days_text": "매주 화·수요일(2일) 휴진",
    "hours_text": "10:00 ~ 18:00 (매주 화·수요일 휴진 / 토·일 주말 정상진료 / 점심시간 12:00 ~ 13:30)",
    "notice_text": "* 접수 마감은 진료 종료 30분 전까지입니다.\n* 주말(토·일)에도 평일과 동일하게 오전 10시부터 오후 6시까지 정상 진료합니다.",
    "doctor_bio": "아이들의 건강한 성장과 밝은 미소를 위해 따뜻하고 세심하게 진료합니다. 우리 아이의 평생 주치의가 되어드리겠습니다.",
    "specialties": [
        "소아청소년과 일반 진료",
        "영유아 건강검진",
        "국가 필수 예방접종",
        "소아 감기·호흡기 질환",
        "소아 알레르기·아토피·비염",
        "소아 소화기·성장 발달 상담"
    ]
}

def load_clinic_info() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CLINIC_INFO_FILE):
        try:
            with open(CLINIC_INFO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = {**DEFAULT_CLINIC_INFO, **data}
                return merged
        except Exception as e:
            logger.warning(f"Failed to read clinic_info.json: {e}")
    try:
        with open(CLINIC_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CLINIC_INFO, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to create default clinic_info.json: {e}")
    return dict(DEFAULT_CLINIC_INFO)

def save_clinic_info(info_dict: dict) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    current = load_clinic_info()
    current.update(info_dict)
    with open(CLINIC_INFO_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    _sync_module_variables(current)
    return current

def reset_clinic_info() -> dict:
    return save_clinic_info(DEFAULT_CLINIC_INFO)

def get_clinic_info() -> dict:
    return load_clinic_info()

# Synchronize module-level variables
_info = load_clinic_info()

CLINIC_INSUCODE = os.getenv("EMR_CLINIC_INSUCODE", _info.get("clinic_insucode", "41334655"))
CLINIC_NAME = os.getenv("EMR_CLINIC_NAME", _info.get("clinic_name", "김기중 소아청소년과의원"))

DEFAULT_ROOM_CODE = int(_info.get("room_code", 1))
DEFAULT_ROOM_NAME = _info.get("room_name", "제1진료실")
DEFAULT_DEPT_CODE = str(_info.get("dept_code", "11"))
DEFAULT_DEPT_NAME = _info.get("dept_name", "소아청소년과")
DEFAULT_DOCTOR_CODE = str(_info.get("doctor_code", "63221"))
DEFAULT_DOCTOR_NAME = os.getenv("EMR_DEFAULT_DOCTOR_NAME", _info.get("doctor_name", "김기중"))

CLINIC_OPEN_TIME = os.getenv("CLINIC_OPEN_TIME", _info.get("open_time", "10:00"))
CLINIC_CLOSE_TIME = os.getenv("CLINIC_CLOSE_TIME", _info.get("close_time", "18:00"))
CLINIC_LUNCH_START = os.getenv("CLINIC_LUNCH_START", _info.get("lunch_start", "12:00"))
CLINIC_LUNCH_END = os.getenv("CLINIC_LUNCH_END", _info.get("lunch_end", "13:30"))
CLINIC_HOURS_TEXT = os.getenv("CLINIC_HOURS_TEXT", _info.get("hours_text", "10:00 ~ 18:00"))
CLINIC_WEEKEND_OPEN = _info.get("weekend_open", True)
CLINIC_CLOSED_WEEKDAYS = _info.get("closed_weekdays", [1, 2])
CLINIC_CLOSED_DAYS_TEXT = _info.get("closed_days_text", "매주 화·수요일(2일) 휴진")

def _sync_module_variables(data: dict):
    global CLINIC_NAME, CLINIC_INSUCODE, DEFAULT_ROOM_CODE, DEFAULT_ROOM_NAME
    global DEFAULT_DEPT_CODE, DEFAULT_DEPT_NAME, DEFAULT_DOCTOR_CODE, DEFAULT_DOCTOR_NAME
    global CLINIC_OPEN_TIME, CLINIC_CLOSE_TIME, CLINIC_LUNCH_START, CLINIC_LUNCH_END
    global CLINIC_HOURS_TEXT, CLINIC_WEEKEND_OPEN, CLINIC_CLOSED_WEEKDAYS, CLINIC_CLOSED_DAYS_TEXT
    
    CLINIC_NAME = data.get("clinic_name", CLINIC_NAME)
    CLINIC_INSUCODE = data.get("clinic_insucode", CLINIC_INSUCODE)
    DEFAULT_ROOM_CODE = int(data.get("room_code", DEFAULT_ROOM_CODE))
    DEFAULT_ROOM_NAME = data.get("room_name", DEFAULT_ROOM_NAME)
    DEFAULT_DEPT_CODE = str(data.get("dept_code", DEFAULT_DEPT_CODE))
    DEFAULT_DEPT_NAME = data.get("dept_name", DEFAULT_DEPT_NAME)
    DEFAULT_DOCTOR_CODE = str(data.get("doctor_code", DEFAULT_DOCTOR_CODE))
    DEFAULT_DOCTOR_NAME = data.get("doctor_name", DEFAULT_DOCTOR_NAME)
    CLINIC_OPEN_TIME = data.get("open_time", CLINIC_OPEN_TIME)
    CLINIC_CLOSE_TIME = data.get("close_time", CLINIC_CLOSE_TIME)
    CLINIC_LUNCH_START = data.get("lunch_start", CLINIC_LUNCH_START)
    CLINIC_LUNCH_END = data.get("lunch_end", CLINIC_LUNCH_END)
    CLINIC_HOURS_TEXT = data.get("hours_text", CLINIC_HOURS_TEXT)
    CLINIC_WEEKEND_OPEN = bool(data.get("weekend_open", CLINIC_WEEKEND_OPEN))
    CLINIC_CLOSED_WEEKDAYS = list(data.get("closed_weekdays", CLINIC_CLOSED_WEEKDAYS))
    CLINIC_CLOSED_DAYS_TEXT = data.get("closed_days_text", CLINIC_CLOSED_DAYS_TEXT)
