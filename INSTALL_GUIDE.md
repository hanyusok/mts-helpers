# 김기중 소아청소년과의원 mts-helpers Clean PC 무인 설치 가이드

이 문서는 아무런 개발 도구나 라이브러리가 설치되어 있지 않은 **완전한 클린 상태의 Windows PC (Windows 10, 11 또는 Windows Server)**에 `mts-helpers`를 설치하고 백그라운드 서비스로 구동하는 절차를 설명합니다.

---

## 📋 설치 전 준비 사항

1. `mts-helpers` 폴더 전체를 새 컴퓨터의 원하는 위치(예: `C:\mts-helpers` 또는 `C:\Users\han\mts-helpers`)에 복사합니다.
2. 진료실 EMR 컴퓨터(Firebird DB 호스트, 기본: `192.168.0.12`)와 동일한 원내 로컬 네트워크(LAN/Wi-Fi)에 연결되어 있어야 합니다.

---

## 🛠️ 단계별 설치 절차 (총 3단계)

### [1단계] 필수 환경 및 방화벽 자동 설치
> **소요 시간: 약 1~2분 (관리자 권한 필요)**

1. `scripts` 폴더로 이동합니다.
2. **`1_install_clean_pc_prerequisites.ps1`** 파일을 마우스 우클릭한 후 **[PowerShell에서 실행]** 또는 관리자 권한 PowerShell에서 실행합니다:
   ```powershell
   cd C:\Users\han\mts-helpers\scripts
   .\1_install_clean_pc_prerequisites.ps1
   ```
3. **스크립트가 자동으로 수행하는 작업**:
   * **Python 3.12** 무인 설치 및 시스템 PATH 자동 등록
   * **Node.js LTS** 무인 설치 (필요 시)
   * **Firebird Client DLL (`fbclient.dll`)**을 `C:\Windows\System32\` 시스템 경로에 자동 복사
   * **Windows 고급 방화벽**에 포트 `3010 (TCP)` 인바운드 허용 규칙 자동 등록 (원내 스마트폰/태블릿/모니터 접속용)

---

### [2단계] Python 가상환경 및 패키지 설치
> **소요 시간: 약 30초**

1. `scripts\2_setup_env.bat` 파일을 **더블클릭**하여 실행합니다.
2. **배치 파일이 자동으로 수행하는 작업**:
   * 프로젝트 폴더 내 격리된 가상환경(`venv`) 생성
   * 최신 `pip` 업그레이드
   * `requirements.txt`에 명시된 필수 의존성 패키지 설치 (`fastapi`, `uvicorn`, `fdb`, `pydantic`, `websockets` 등)

---

### [3단계] 원격 EMR IP 확인 및 테스트 구동

1. `config.py` 파일을 메모장이나 에디터로 열어 **EMR 컴퓨터 IP**가 맞는지 확인합니다:
   ```python
   # 진료실 컴퓨터 IP (기본값: 192.168.0.12)
   DB_HOST = os.getenv("EMR_DB_HOST", "192.168.0.12")
   DB_PORT = int(os.getenv("EMR_DB_PORT", "3050"))
   ```
2. `scripts\run_dev.bat` 파일을 더블클릭하여 콘솔 창에서 서버를 시작합니다.
3. 웹 브라우저를 열고 다음 주소에 접속하여 확인합니다:
   * **메인 안내 페이지**: `http://localhost:3010/`
   * **모바일 간편접수**: `http://localhost:3010/quick/`
   * **실시간 대기열**: `http://localhost:3010/quicklist/`
   * **대기실 DID 전광판**: `http://localhost:3010/signage/`
4. 정상 동작을 확인한 후 콘솔 창을 닫습니다 (`Ctrl + C`).

---

### [4단계] Windows 24시간 무인 백그라운드 서비스 등록
> **PC 부팅 시 로그인하지 않아도 전원만 켜지면 365일 자동으로 백그라운드에서 실행됩니다.**

1. PowerShell을 **관리자 권한(Run as Administrator)**으로 엽니다.
2. 다음 스크립트를 실행합니다:
   ```powershell
   cd C:\Users\han\mts-helpers\scripts
   .\3_install_service.ps1
   ```
3. **스크립트가 자동으로 수행하는 작업**:
   * 경량 서비스 관리자(`nssm.exe`) 준비
   * `MTS_Helpers_Service` 윈도우 서비스 자동 등록
   * 부팅 시 자동 시작(`SERVICE_AUTO_START`) 설정
   * 콘솔 로그를 `logs\service.log`에 10MB 단위 자동 회전(Rotation) 저장 설정
   * 서비스 즉시 시작

---

## 🔧 서비스 일상 관리 방법

`scripts` 폴더 내에 배치된 간편 배치 파일을 더블클릭하여 제어할 수 있습니다:
* **서비스 시작**: `scripts\start_service.bat`
* **서비스 중지**: `scripts\stop_service.bat`
* **서비스 재시작**: `scripts\restart_service.bat`
* **로그 확인**: `logs\service.log` 파일을 메모장으로 열어 실시간 EMR 연동 상태 및 접속 로그 확인

---

## ❓ 문제 해결 (Troubleshooting)

### 1. "현재 진료시간이 아니거나 진료준비중입니다" 문구가 계속 뜰 때
* 원격 진료실 PC(`192.168.0.12`)가 켜져 있는지 확인하세요.
* 원격 PC의 Firebird 서비스가 실행 중인지 확인하세요 (`포트 3050`).
* PowerShell에서 연결 테스트 명령을 실행해 보세요:
  ```powershell
  Test-NetConnection -ComputerName 192.168.0.12 -Port 3050
  ```
  `TcpTestSucceeded : True` 가 나오면 정상 연결 상태입니다.

### 2. 스마트폰이나 대기실 모니터에서 접속이 안 될 때
* `mts-helpers`가 실행 중인 PC의 로컬 IP(예: `192.168.0.50`)를 확인합니다 (`ipconfig`).
* 스마트폰에서 `http://192.168.0.50:3010/quick/` 으로 접속합니다.
* 접속이 차단된다면 `1_install_clean_pc_prerequisites.ps1`을 관리자 권한으로 실행하여 방화벽 3010 포트가 열려 있는지 다시 확인하세요.

### 3. 공인인증서 등록 및 건강보험 자격조회 / 진료비 계산 연동 안내
* **`mts-helpers` 독립성**: `mts-helpers`는 김기중소아청소년과의원 독립 패키지로, 내부에는 어떠한 타 병원(마트의원 등) 인증서도 포함되어 있지 않습니다.
* **타 병원 인증서 보존**: PC 또는 타 시스템(`mts-gtw` 등)에 기존 설치된 마트의원 인증서는 고유 업무용이므로 **절대 삭제하지 마십시오**.
* **김기중의원 공인인증서 등록**:
  - 건강보험공단 자격조회 및 심평원 진료비 계산/청구는 원내 메인 EMR(`Mts3`/`DeskPro`)에서 처리됩니다.
  - 김기중의원 보건복지부 공인인증서(요양기관기호 41334655)를 `C:\Users\han\AppData\LocalLow\NPKI\KICA\USER\` 또는 `C:\NPKI\KICA\User\` 폴더에 배치하고, EMR 환경설정에서 해당 인증서를 등록하시면 됩니다.

