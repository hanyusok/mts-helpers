@echo off
setlocal
chcp 65001 > nul

echo ============================================================
echo   김기중 소아청소년과의원 MTS Helpers 서비스 재시작
echo ============================================================

sc query MTS_Helpers_Service > nul 2>&1
if errorlevel 1 (
    echo [경고] MTS_Helpers_Service 서비스가 등록되어 있지 않습니다.
    pause
    exit /b 1
)

net stop MTS_Helpers_Service
timeout /t 2 /nobreak > nul
net start MTS_Helpers_Service
echo.
pause
