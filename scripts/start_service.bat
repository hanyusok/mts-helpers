@echo off
setlocal
chcp 65001 > nul

echo ============================================================
echo   김기중 소아청소년과의원 MTS Helpers 서비스 시작
echo ============================================================

sc query MTS_Helpers_Service > nul 2>&1
if errorlevel 1 (
    echo [경고] MTS_Helpers_Service 서비스가 아직 Windows에 설치되지 않았습니다.
    echo 먼저 관리자 권한 PowerShell에서 아래 스크립트를 실행해 서비스를 등록하세요:
    echo   powershell -ExecutionPolicy Bypass -File "%~dp03_install_service.ps1"
    echo.
    echo [대안] 지금 바로 테스트 실행하시려면 run_dev.bat 을 실행하세요.
    echo ============================================================
    pause
    exit /b 1
)

echo 서비스를 시작하는 중입니다...
net start MTS_Helpers_Service
echo.
pause
