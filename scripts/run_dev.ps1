# ==============================================================================
# run_dev.ps1: 개발/디버그 모드 실행 (포트 3001, 핫 리로드 활성화)
# ==============================================================================
$Host.UI.RawUI.WindowTitle = "MTS Helpers [DEVELOPMENT 3001]"
$env:APP_ENV = "development"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  김기중 소아청소년과의원 MTS Helpers [개발/디버그 모드]      " -ForegroundColor Cyan
Write-Host "  주소: http://localhost:3001/ (핫 리로드 활성화)             " -ForegroundColor Green
Write-Host "  (종료하려면 Ctrl + C 를 누르세요)                           " -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$pythonExe = Join-Path $projectDir "venv\Scripts\python.exe"
if (Test-Path $pythonExe) {
    & $pythonExe main.py
} else {
    python main.py
}
