@echo off
setlocal
chcp 65001 > nul

echo ============================================================
echo   김기중 소아청소년과의원 MTS Helpers [운영/프로덕션 모드]
echo   포트: http://localhost:3001/ (고성능 단독 프로세스)
echo   (종료하려면 이 창에서 Ctrl + C 를 누르세요)
echo ============================================================
echo.

set APP_ENV=production
cd /d "%~dp0.."

if exist "venv\Scripts\python.exe" goto USE_VENV
goto USE_SYSTEM

:USE_VENV
echo [안내] 가상환경(venv) Python으로 운영 서버를 실행합니다...
venv\Scripts\python.exe main.py
goto END

:USE_SYSTEM
echo [안내] 시스템 Python으로 운영 서버를 실행합니다...
python main.py
goto END

:END
echo.
echo 서버가 종료되었습니다.
pause
