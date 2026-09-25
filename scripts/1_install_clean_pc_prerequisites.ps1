# ==============================================================================
# 1_install_clean_pc_prerequisites.ps1
# 김기중 소아청소년과의원 mts-helpers Clean PC 필수 유틸리티 무인 설치 스크립트
# 관리자 권한(Run as Administrator)으로 실행해야 합니다.
# ==============================================================================

param (
    [switch]$InstallPostgres = $false,
    [switch]$InstallNode = $true,
    [switch]$InstallGit = $false
)

# 1. 관리자 권한 확인
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "이 스크립트는 관리자 권한으로 실행해야 합니다. 관리자 권한으로 다시 실행합니다..."
    Start-Process powershell.exe -ArgumentList ("-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"") -Verb RunAs
    exit
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   김기중 소아청소년과의원 mts-helpers Clean PC 사전 환경 자동 설치 시작   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 2. winget 확인
$hasWinget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $hasWinget) {
    Write-Warning "winget (Windows Package Manager)을 찾을 수 없습니다. 공식 웹사이트 설치를 권장합니다."
}

# 3. Python 3.12 설치 확인 및 설치
Write-Host "`n[1/5] Python 설치 상태 확인..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    $pyVer = & python --version
    Write-Host "  -> Python 이미 설치됨: $pyVer" -ForegroundColor Green
} else {
    Write-Host "  -> Python이 감지되지 않았습니다. winget을 통해 Python 3.12 설치를 시작합니다..." -ForegroundColor Yellow
    if ($hasWinget) {
        winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        # 환경변수 PATH 즉시 갱신
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  -> Python 3.12 설치 완료" -ForegroundColor Green
    } else {
        Write-Host "  -> winget 부재로 공식 웹 인스톨러 다운로드 진행..." -ForegroundColor Yellow
        $installerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        $installerPath = "$env:TEMP\python-3.12-installer.exe"
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
        Start-Process -Wait -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1"
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "  -> Python 3.12 설치 완료" -ForegroundColor Green
    }
}

# 4. Node.js LTS 설치 확인 및 설치
if ($InstallNode) {
    Write-Host "`n[2/5] Node.js 설치 상태 확인..." -ForegroundColor Yellow
    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($node) {
        $nodeVer = & node --version
        Write-Host "  -> Node.js 이미 설치됨: $nodeVer" -ForegroundColor Green
    } else {
        Write-Host "  -> Node.js LTS 설치를 시작합니다..." -ForegroundColor Yellow
        if ($hasWinget) {
            winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "  -> Node.js LTS 설치 완료" -ForegroundColor Green
        } else {
            Write-Warning "winget을 통해 Node.js를 설치할 수 없습니다. nodejs.org에서 수동 다운로드 바랍니다."
        }
    }
}

# 5. PostgreSQL 설치 (선택 옵션)
if ($InstallPostgres) {
    Write-Host "`n[3/5] PostgreSQL 설치 확인..." -ForegroundColor Yellow
    $psql = Get-Command psql -ErrorAction SilentlyContinue
    if ($psql) {
        Write-Host "  -> PostgreSQL 이미 설치됨" -ForegroundColor Green
    } else {
        Write-Host "  -> PostgreSQL 16 설치 진행..." -ForegroundColor Yellow
        if ($hasWinget) {
            winget install PostgreSQL.PostgreSQL.16 --silent --accept-package-agreements --accept-source-agreements
            Write-Host "  -> PostgreSQL 설치 완료" -ForegroundColor Green
        }
    }
} else {
    Write-Host "`n[3/5] PostgreSQL 설치 건너뜀 (필요 시 -InstallPostgres 옵션 사용)" -ForegroundColor DarkGray
}

# 6. Firebird Client DLL (fbclient.dll) 시스템 등록
Write-Host "`n[4/5] Firebird Client DLL (fbclient.dll) 확인 및 시스템 경로 복사..." -ForegroundColor Yellow
$scriptDir = Split-Path -Parent $PSCommandPath
$projectDir = Split-Path -Parent $scriptDir
$localFbClient = Join-Path $projectDir "fbclient.dll"

if (Test-Path $localFbClient) {
    $sys32Path = "C:\Windows\System32\fbclient.dll"
    if (-not (Test-Path $sys32Path)) {
        try {
            Copy-Item -Path $localFbClient -Destination $sys32Path -Force
            Write-Host "  -> fbclient.dll을 C:\Windows\System32에 성공적으로 복사했습니다." -ForegroundColor Green
        } catch {
            Write-Warning "  -> C:\Windows\System32 복사 실패 ($_.Exception.Message). 프로젝트 폴더 내의 DLL을 직접 사용합니다."
        }
    } else {
        Write-Host "  -> C:\Windows\System32\fbclient.dll이 이미 존재합니다." -ForegroundColor Green
    }
} else {
    Write-Warning "  -> 프로젝트 폴더에 fbclient.dll이 없습니다. Firebird 드라이버가 필요합니다."
}

# 7. Windows 고급 방화벽 포트 3001(TCP) 인바운드 허용
Write-Host "`n[5/5] Windows 방화벽 인바운드 규칙 등록 (포트 3001)..." -ForegroundColor Yellow
$ruleName = "MTS_Helpers_Port_3001"
$existingRule = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    New-NetFirewallRule -Name $ruleName `
        -DisplayName "김기중 소아청소년과의원 모바일접수/대기열 (Port 3001)" `
        -Direction Inbound `
        -LocalPort 3001 `
        -Protocol TCP `
        -Action Allow | Out-Null
    Write-Host "  -> 방화벽 인바운드 포트 3001 허용 규칙 등록 완료!" -ForegroundColor Green
} else {
    Write-Host "  -> 방화벽 규칙 ($ruleName)이 이미 등록되어 있습니다." -ForegroundColor Green
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "   Clean PC 사전 환경 설치가 성공적으로 완료되었습니다!     " -ForegroundColor Cyan
Write-Host "   다음 단계: scripts\2_setup_env.bat 을 실행하세요.        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
