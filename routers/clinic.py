import datetime
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Body

from config import get_clinic_info, save_clinic_info, reset_clinic_info
from database.firebird import check_remote_server_alive

logger = logging.getLogger("clinic_router")

router = APIRouter()

@router.get("/clinic/info")
def get_clinic_profile():
    """Returns the full clinic configuration, including name, address, hours, and doctor profile."""
    return get_clinic_info()

@router.post("/clinic/info")
def update_clinic_profile(payload: Dict[str, Any] = Body(...)):
    """
    Updates the clinic configuration and saves it to clinic_info.json.
    Automatically recalculates hours summary text if open/close/closed days change.
    """
    try:
        updated = save_clinic_info(payload)
        logger.info(f"Clinic information updated: {updated.get('clinic_name')}")
        return {
            "status": "success",
            "message": "병원 정보가 성공적으로 저장되었습니다.",
            "data": updated
        }
    except Exception as e:
        logger.error(f"Failed to update clinic info: {e}")
        raise HTTPException(status_code=500, detail=f"병원 정보 저장 중 오류 발생: {str(e)}")

@router.post("/clinic/info/reset")
def reset_clinic_profile():
    """Resets the clinic configuration to default settings."""
    try:
        reset_data = reset_clinic_info()
        return {
            "status": "success",
            "message": "병원 정보가 기본 설정으로 초기화되었습니다.",
            "data": reset_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clinic/status")
def get_clinic_status():
    """
    Returns operating status of the clinic and the doctor's PC / remote Firebird server.
    Used by /quick, /quicklist, and root page to display status banners and disable registration when closed.
    Dynamically loads latest clinic settings.
    """
    info = get_clinic_info()
    clinic_open_time = info.get("open_time", "10:00")
    clinic_close_time = info.get("close_time", "18:00")
    clinic_lunch_start = info.get("lunch_start", "12:00")
    clinic_lunch_end = info.get("lunch_end", "13:30")
    clinic_hours_text = info.get("hours_text", f"{clinic_open_time} ~ {clinic_close_time}")
    clinic_weekend_open = info.get("weekend_open", True)
    clinic_closed_weekdays = info.get("closed_weekdays", [1, 2])
    clinic_closed_days_text = info.get("closed_days_text", "매주 화·수요일(2일) 휴진")
    clinic_name = info.get("clinic_name", "김기중 소아청소년과의원")

    server_alive = check_remote_server_alive(timeout=1.2)
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    current_weekday = now.weekday()

    if not server_alive:
        return {
            "can_checkin": False,
            "is_open": False,
            "server_alive": False,
            "clinic_name": clinic_name,
            "reason": "SERVER_STOPPED",
            "message": "진료실 원격 서버가 종료(Stop)되어 있거나 진료시간이 아닙니다. 진료시간 외에는 모바일 접수가 불가합니다.",
            "clinic_hours_text": clinic_hours_text,
            "current_time": current_time,
            "is_lunch_time": False
        }

    is_closed_day = current_weekday in clinic_closed_weekdays
    is_weekend = current_weekday in (5, 6)
    is_lunch_time = clinic_lunch_start <= current_time < clinic_lunch_end
    is_working_hours = clinic_open_time <= current_time < clinic_close_time

    if is_closed_day:
        can_checkin = False
        is_open = False
        reason = "CLOSED_DAY"
    elif is_weekend and not clinic_weekend_open:
        can_checkin = False
        is_open = False
        reason = "WEEKEND_CLOSED"
    elif not is_working_hours:
        can_checkin = False
        is_open = False
        reason = "OUT_OF_HOURS"
    elif is_lunch_time:
        can_checkin = False
        is_open = True
        reason = "LUNCH_TIME"
    else:
        can_checkin = True
        is_open = True
        reason = "OPEN"

    if not can_checkin:
        message = "현재 진료시간이 아니거나 진료준비중입니다. 진료시간에 접수해 주시기 바랍니다."
        if reason == "SERVER_STOPPED":
            message = "진료실 원격 서버가 종료되어 있어 접수가 불가합니다."
        elif reason == "CLOSED_DAY":
            message = f"오늘은 {clinic_closed_days_text}입니다. (진료일: 목·금·토·일·월 {clinic_open_time}~{clinic_close_time})"
        elif reason == "LUNCH_TIME":
            message = f"현재 점심시간({clinic_lunch_start}~{clinic_lunch_end})입니다. 점심시간 이후 접수가 가능합니다."
        elif reason == "WEEKEND_CLOSED":
            message = f"주말 휴진일입니다. ({clinic_hours_text})"
        elif reason == "OUT_OF_HOURS":
            message = f"현재는 진료시간이 아닙니다. ({clinic_hours_text})"
    else:
        message = f"현재 정상 접수 가능한 진료시간입니다. ({clinic_hours_text})"

    return {
        "can_checkin": can_checkin,
        "is_open": is_open,
        "server_alive": server_alive,
        "clinic_name": clinic_name,
        "reason": reason,
        "message": message,
        "clinic_hours_text": clinic_hours_text,
        "current_time": current_time,
        "is_lunch_time": is_lunch_time
    }
