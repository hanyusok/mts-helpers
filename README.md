# 김기중 소아청소년과의원 접수 및 대기열 서비스 (mts-helpers)

김기중 소아청소년과의원 전용의 경량화된 독립 서비스 패키지입니다.  
병원 내원 환자를 위한 **모바일 간편접수(`/quick`)**, **실시간 대기현황(`/quicklist`)**, **대기실 DID 전광판(`/signage`)**, **병원 위치 및 안내 메인 페이지(`/`)**, 그리고 **병원 정보 관리 UI(`/admin/`)**를 제공합니다.

---

## 🌟 주요 기능 및 서비스 경로

| 경로 (URL) | 서비스명 | 설명 |
| :--- | :--- | :--- |
| `http://localhost:3010/` | **김기중 소아청소년과의원 메인** | 진료시간, 의료진(김기중 원장), 병원 위치(매교역 2번 출구), 실시간 진료 상태, 주요 서비스 바로가기 |
| `http://localhost:3010/admin/` | **병원 정보 관리 콘솔** | 병원명, 진료시간, 주소, 네이버 지도 링크, 원장 소개 및 진료과목을 웹에서 실시간 편집 및 저장 |
| `http://localhost:3010/quick/` | **모바일 간편 접수** | 스마트폰으로 성명 + 생년월일 입력하여 당일 진료 원터치 접수 |
| `http://localhost:3010/quicklist/` | **실시간 대기열** | 환자가 자신의 진료 순서와 실시간 대기 인원을 스마트폰으로 확인 |
| `http://localhost:3010/signage/` | **대기실 DID 전광판** | 대기실 대형 모니터/TV용 현재 진료 중 및 다음 대기자 안내 화면 |

---

## 📍 병원 위치 안내
* **위치**: 매교역 2번 출구 (경기 수원시 팔달구)
* **대중교통**: 수인분당선 매교역 2번 출구 바로 앞
* **네이버 지도 바로가기**: [https://naver.me/GgUzsloE](https://naver.me/GgUzsloE)

---

## 📁 디렉토리 구조

```
C:\Users\han\mts-helpers\
├── static/                 # 루트(/) 메인 안내 페이지 (index.html, styles.css)
├── admin-ui/               # 병원 정보 관리 웹 UI 콘솔 (/admin/)
├── quick-ui/               # 모바일 간편 접수 웹 UI (/quick/)
├── quicklist-ui/           # 실시간 대기열 모바일 웹 UI (/quicklist/)
├── signage-ui/             # 대기실 DID 전광판 웹 UI (/signage/)
├── data/                   # 병원 설정 파일 저장소 (clinic_info.json)
├── database/               # Firebird DB 연동 및 실시간 변경 감지기
├── repositories/           # 환자 조회 및 대기열 DB 데이터 접근 계층
├── services/               # 간편 접수 및 검증 비즈니스 로직
├── routers/                # REST API 및 WebSocket 라우터 (clinic, patients, queue, websockets)
├── scripts/                # Clean PC 자동 설치 및 서비스 관리 스크립트
├── config.py               # 서버 포트(3010), EMR DB 호스트 및 병원 설정 관리
├── main.py                 # FastAPI 애플리케이션 진입점
├── requirements.txt        # Python 필수 패키지 목록
└── fbclient.dll            # Firebird 32-bit 클라이언트 라이브러리
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 테스트 실행 (콘솔 모드)
가상환경이 구축된 상태에서 아래 스크립트를 더블클릭합니다:
```cmd
scripts\run_dev.bat
```
브라우저에서 `http://localhost:3010` 으로 접속하여 정상 작동을 확인합니다.

### 2. 새 컴퓨터(Clean PC) 설치 안내
아무것도 설치되지 않은 새 Windows PC에 설치할 경우 **[INSTALL_GUIDE.md](file:///C:/Users/han/mts-helpers/INSTALL_GUIDE.md)**를 참조하세요.
단 3단계 스크립트 실행으로 모든 환경이 자동 구축됩니다:
1. `scripts\1_install_clean_pc_prerequisites.ps1` (관리자 권한 실행)
2. `scripts\2_setup_env.bat` (가상환경 및 라이브러리 자동 설치)
3. `scripts\3_install_service.ps1` (Windows 백그라운드 서비스 등록)

---

## ⚙️ 병원 정보 변경 및 설정 방법
1. **웹 브라우저 UI를 통한 실시간 변경 (가장 편리한 방법)**:
   - 메인 화면(`http://localhost:3010/`) 우측 상단의 `[병원 정보 관리 ⚙️]` 버튼을 누르거나,
   - `http://localhost:3010/admin/` 으로 접속하여 병원명, 진료시간, 위치, 네이버 지도 링크, 의료진 소개를 손쉽게 수정하고 [저장하기]를 누르면 즉시 전체 시스템에 반영됩니다.
2. **설정 파일 직접 수정**:
   - `data/clinic_info.json` 파일의 값을 수정하거나 `config.py`의 기본값을 수정할 수 있습니다.

---

## 🔐 진료비 계산, 건강보험 자격조회 및 공인인증서 운영 정책

### 1. 진료비 계산 및 건강보험 자격조회 기능 분리
* **`mts-helpers`**: 환자 모바일 간편접수(`/quick`), 실시간 대기열(`/quicklist`), 대기실 전광판(`/signage`)을 전담하는 경량 마이크로서비스입니다. 서비스 경량화와 환자 개인정보 보호를 위해 인증서 파일이나 진료비 계산/자격조회 로직을 자체 보관하지 않습니다.
* **원내 EMR (`Mts3` / `DeskPro` / `InsuPro`)**: 당일 진료비 계산, 본인부담금/공단부담금 산정, 수납 영수증 발행 및 국민건강보험공단(NHIS) 실시간 수진자 자격조회는 메인 EMR 프로그램을 통해 수행됩니다.

### 2. 공인인증서 독립 분리 원칙 (김기중 소아청소년과의원)
* **독립성 유지**: `mts-helpers`는 **김기중 소아청소년과의원(요양기관기호: 41334655)** 전용 프로젝트입니다.
* **타 기관 인증서 보존 주의**: PC 또는 타 게이트웨이(`mts-gtw` 등)에 설치된 기존 타 의료기관(예: 마트의원 등)의 공인인증서는 각 기관 고유 업무용이므로 **절대 삭제하거나 덮어쓰지 않고 보존**해야 합니다.
* **김기중의원 공인인증서 설치 경로**:
  - Windows 사용자 NPKI 표준 경로:  
    `C:\Users\han\AppData\LocalLow\NPKI\KICA\USER\cn=김기중소아청소년과의원1,ou=건강보험,ou=MOHW RA센터...`
  - 시스템 NPKI 공용 경로:  
    `C:\NPKI\KICA\User\cn=김기중소아청소년과의원1,ou=건강보험...`
  - 필수 파일: `signCert.der`, `signPri.key`, `kmCert.der`, `kmPri.key`
  - 웹 관리 콘솔(`http://localhost:3010/admin/`)의 **'5. 김기중소아청소년과의원 공인인증서 설치 및 연동 안내'**에서도 상세 가이드를 언제든지 확인할 수 있습니다.

