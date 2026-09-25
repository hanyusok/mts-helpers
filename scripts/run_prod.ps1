# ==============================================================================
# run_prod.ps1: 실운영/프로덕션 모드 실행 (포트 3001, 고성능 프로세스)
# ==============================================================================
$Host.UI.RawUI.WindowTitle = "MTS Helpers [PRODUCTION 3001]"
$env:APP_ENV = "production"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

Write-Host "============================================================" -ForegroundColor Green
Write-Host "  김기중 소아청소년과의원 MTS Helpers [실운영/프로덕션 모드]  " -ForegroundColor Green
Write-Host "  주소: http://localhost:3001/ (최적화 단독 프로세스)          " -ForegroundColor Cyan
Write-Host "  (종료하려면 Ctrl + C 를 누르세요)                           " -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Green

$pythonExe = Join-Path $projectDir "venv\Scripts\python.exe"
if (Test-Path $pythonExe) {
    & $pythonExe main.py
} else {
    python main.py
}
