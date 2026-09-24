@echo off
chcp 65001 > nul
setlocal

echo ============================================================
echo   김기중 소아청소년과의원 mts-helpers 가상환경 및 라이브러리 설치
echo ============================================================

cd /d "%~dp0\.."

:: 1. Python 설치 확인
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 시스템 PATH에 등록되어 있지 않습니다.
    echo 1_install_clean_pc_prerequisites.ps1 을 먼저 실행하여 Python을 설치해 주세요.
    pause
    exit /b 1
)

:: 2. venv 가상환경 생성
if not exist "venv" (
    echo.
    echo [1/3] Python venv 가상환경 생성 중...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
    echo  - 가상환경(venv) 생성 완료!
) else (
    echo.
    echo [1/3] 기존 venv 가상환경이 이미 존재합니다.
)

:: 3. pip 업그레이드
echo.
echo [2/3] pip 최신 버전 업그레이드 중...
call venv\Scripts\python.exe -m pip install --upgrade pip --quiet

:: 4. requirements.txt 설치
echo.
echo [3/3] 필수 의존성 패키지 설치 중 (fastapi, uvicorn, fdb, pydantic, websockets)...
call venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [오류] 라이브러리 설치 중 오류가 발생했습니다. 네트워크 연결을 확인해 주세요.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   가상환경 및 필수 라이브러리 설치가 성공적으로 완료되었습니다!
echo   다음 단계:
echo     - 직접 테스트: scripts\run_dev.bat 실행
echo     - 서비스 등록: scripts\3_install_service.ps1 (관리자 권한 실행)
echo ============================================================
echo.
pause
