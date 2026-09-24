# ==============================================================================
# 3_install_service.ps1
# 김기중 소아청소년과의원 mts-helpers Windows 백그라운드 서비스(NSSM) 자동 등록 스크립트
# 관리자 권한(Run as Administrator)으로 실행해야 합니다.
# ==============================================================================

# 1. 관리자 권한 확인
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "이 스크립트는 관리자 권한으로 실행해야 합니다. 관리자 권한으로 다시 실행합니다..."
    Start-Process powershell.exe -ArgumentList ("-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"") -Verb RunAs
    exit
}

$scriptDir = Split-Path -Parent $PSCommandPath
$projectDir = Split-Path -Parent $scriptDir
$serviceName = "MTS_Helpers_Service"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   김기중 소아청소년과의원 mts-helpers Windows 백그라운드 서비스 등록   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 2. Python 가상환경 인터프리터 확인
$pythonExe = Join-Path $projectDir "venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[오류] 가상환경(venv\Scripts\python.exe)을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "먼저 scripts\2_setup_env.bat 을 실행하여 가상환경을 생성해 주세요." -ForegroundColor Yellow
    pause
    exit 1
}

# 3. NSSM 다운로드 확인
$nssmExe = Join-Path $projectDir "nssm.exe"
if (-not (Test-Path $nssmExe)) {
    Write-Host "`n[1/4] NSSM (서비스 매니저) 다운로드 및 준비 중..." -ForegroundColor Yellow
    $zipPath = Join-Path $env:TEMP "nssm.zip"
    $extractPath = Join-Path $env:TEMP "nssm_extracted"
    
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
        
        # 64비트 바이너리 복사
        $srcNssm = Join-Path $extractPath "nssm-2.24\win64\nssm.exe"
        if (-not (Test-Path $srcNssm)) {
            $srcNssm = Join-Path $extractPath "nssm-2.24\win32\nssm.exe"
        }
        Copy-Item -Path $srcNssm -Destination $nssmExe -Force
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
        Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  -> NSSM 다운로드 및 배치 완료!" -ForegroundColor Green
    } catch {
        Write-Warning "  -> 공식 웹 다운로드 실패: $($_.Exception.Message)"
        Write-Host "수동으로 nssm.exe를 $projectDir 폴더에 배치해 주세요." -ForegroundColor Yellow
        pause
        exit 1
    }
}

# 4. 로그 디렉토리 생성
$logDir = Join-Path $projectDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir "service.log"

# 5. 기존 서비스 중지 및 제거 (이미 등록되어 있을 경우)
Write-Host "`n[2/4] 기존 서비스 상태 점검..." -ForegroundColor Yellow
$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  -> 기존 등록된 $serviceName 서비스를 중지하고 업데이트합니다..." -ForegroundColor Yellow
    & $nssmExe stop $serviceName | Out-Null
    Start-Sleep -Seconds 1
    & $nssmExe remove $serviceName confirm | Out-Null
    Start-Sleep -Seconds 1
}

# 6. NSSM 서비스 등록 및 세부 속성 설정
Write-Host "`n[3/4] $serviceName 서비스 등록 및 환경 설정..." -ForegroundColor Yellow
& $nssmExe install $serviceName "$pythonExe" "main.py"
& $nssmExe set $serviceName AppDirectory "$projectDir"
$serviceDisplayName = "김기중 소아청소년과의원 모바일 접수/대기열 서비스 (MTS Helpers)"
& $nssmExe set $serviceName DisplayName "김기중 소아청소년과의원 모바일 접수/대기열 서비스 (MTS Helpers)"
& $nssmExe set $serviceName Description "김기중 소아청소년과의원 모바일 간편접수(/quick), 실시간 대기열(/quicklist), 대기실 전광판(/signage) 백그라운드 서비스"
& $nssmExe set $serviceName Start SERVICE_AUTO_START
& $nssmExe set $serviceName AppStdout "$logFile"
& $nssmExe set $serviceName AppStderr "$logFile"
& $nssmExe set $serviceName AppRotateFiles 1
& $nssmExe set $serviceName AppRotateBytes 10485760 # 10MB 자동 로테이션

# 7. 서비스 시작
Write-Host "`n[4/4] 서비스 시작..." -ForegroundColor Yellow
& $nssmExe start $serviceName

Start-Sleep -Seconds 2
$svcStatus = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($svcStatus -and $svcStatus.Status -eq "Running") {
    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Host "   서비스가 정상적으로 시작되었습니다! (상태: Running)        " -ForegroundColor Green
    Write-Host "   - 서비스명: $serviceName                                   " -ForegroundColor Green
    Write-Host "   - 자동 시작: PC 부팅 시 로그인 없이 자동 실행              " -ForegroundColor Green
    Write-Host "   - 접속 주소: http://localhost:3010                         " -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
} else {
    Write-Warning "서비스 등록은 완료되었으나 현재 실행 상태가 아닙니다 ($($svcStatus.Status))."
    Write-Host "logs\service.log 파일을 확인해 주세요." -ForegroundColor Yellow
}

pause
