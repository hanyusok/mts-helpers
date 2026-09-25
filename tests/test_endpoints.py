import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from main import app
from config import PORT

client = TestClient(app)

# 1. Test Root
r_root = client.get('/')
assert r_root.status_code == 200, f'Root failed: {r_root.status_code}'
assert '김기중 소아청소년과의원' in r_root.text, 'Root HTML missing clinic name'
assert '매교역' in r_root.text, 'Root HTML missing station name'
assert 'https://naver.me/GgUzsloE' in r_root.text, 'Root HTML missing naver map url'
assert '/kiosk/' in r_root.text, 'Root HTML missing kiosk link'
print(' [PASS] GET / -> 200 OK (김기중 소아청소년과의원 메인페이지 & 위치 안내 & 키오스크 카드)')

# 2. Test /admin
r_admin = client.get('/admin/')
assert r_admin.status_code == 200, f'/admin failed: {r_admin.status_code}'
assert '병원 정보 관리 콘솔' in r_admin.text, 'Admin HTML missing title'
assert '/kiosk/' in r_admin.text, 'Admin HTML missing kiosk link'
print(' [PASS] GET /admin/ -> 200 OK (병원 정보 관리 콘솔)')

# 3. Test /kiosk
r_kiosk = client.get('/kiosk/')
assert r_kiosk.status_code == 200, f'/kiosk failed: {r_kiosk.status_code}'
assert '셀프 체크인' in r_kiosk.text, 'Kiosk HTML missing title'
print(' [PASS] GET /kiosk/ -> 200 OK (원내 무인 키오스크 접수 화면)')

# 4. Test /quick
r_quick = client.get('/quick/')
assert r_quick.status_code == 200, f'/quick failed: {r_quick.status_code}'
print(' [PASS] GET /quick/ -> 200 OK (모바일 간편 접수)')

# 5. Test /quicklist
r_quicklist = client.get('/quicklist/')
assert r_quicklist.status_code == 200, f'/quicklist failed: {r_quicklist.status_code}'
print(' [PASS] GET /quicklist/ -> 200 OK (실시간 대기열)')

# 6. Test /signage
r_signage = client.get('/signage/')
assert r_signage.status_code == 200, f'/signage failed: {r_signage.status_code}'
print(' [PASS] GET /signage/ -> 200 OK (대기실 전광판)')

# 7. Test /config.js & Port 3001
assert PORT == 3001, f'Expected PORT 3001, got {PORT}'
r_config = client.get('/config.js')
assert r_config.status_code == 200, f'/config.js failed: {r_config.status_code}'
assert f'window.GATEWAY_PORT = {PORT};' in r_config.text, 'Config JS missing port'
assert 'window.GATEWAY_PORT = 3001;' in r_config.text, 'Config JS did not return 3001'
print(f' [PASS] GET /config.js -> 200 OK (Port: {PORT} - Verified 3001)')

# 8. Test /api/clinic/info (GET)
r_info = client.get('/api/clinic/info')
assert r_info.status_code == 200, f'/api/clinic/info failed: {r_info.status_code}'
info_data = r_info.json()
assert info_data.get('clinic_name') == '김기중 소아청소년과의원'
assert '매교역' in info_data.get('address')
assert info_data.get('map_url') == 'https://naver.me/GgUzsloE'
print(' [PASS] GET /api/clinic/info -> 200 OK (병원 상세 정보 조회)')

# 9. Test /api/clinic/info (POST edit)
r_edit = client.post('/api/clinic/info', json={'phone': '031-999-8888'})
assert r_edit.status_code == 200, f'/api/clinic/info POST failed: {r_edit.status_code}'
updated_data = client.get('/api/clinic/info').json()
assert updated_data.get('phone') == '031-999-8888'
print(' [PASS] POST /api/clinic/info -> 200 OK (병원 정보 실시간 수정/저장)')

# 10. Test /api/clinic/info/reset
r_reset = client.post('/api/clinic/info/reset')
assert r_reset.status_code == 200
reset_data = client.get('/api/clinic/info').json()
assert reset_data.get('phone') == '031-234-5678'
assert reset_data.get('clinic_name') == '김기중 소아청소년과의원'
print(' [PASS] POST /api/clinic/info/reset -> 200 OK (병원 정보 기본값 복원)')

# 11. Test /api/clinic/status
r_status = client.get('/api/clinic/status')
assert r_status.status_code == 200, f'/api/clinic/status failed: {r_status.status_code}'
data = r_status.json()
assert 'can_checkin' in data, 'Missing can_checkin'
assert data.get('clinic_name') == '김기중 소아청소년과의원'
print(f' [PASS] GET /api/clinic/status -> 200 OK (Clinic: {data.get("clinic_name")}, Status: {data.get("reason")})')

# 12. Test /api/patients (Kiosk lookup endpoint)
r_patients = client.get('/api/patients?pname=테스트')
assert r_patients.status_code in (200, 503), f'/api/patients unexpected status: {r_patients.status_code}'
print(f' [PASS] GET /api/patients -> {r_patients.status_code} (키오스크 환자 조회 API 연동)')

# 13. Test /api/quick/verify validation
r_verify = client.post('/api/quick/verify', json={'pname': '', 'birth': ''})
assert r_verify.status_code == 200
assert r_verify.json()['verified'] is False
print(' [PASS] POST /api/quick/verify -> 200 OK (Graceful validation test)')

# 14. Test Multi-Doctor in /api/clinic/info
r_doctors_info = client.get('/api/clinic/info')
assert r_doctors_info.status_code == 200
docs_data = r_doctors_info.json().get('doctors', [])
assert len(docs_data) >= 3, f'Expected at least 3 doctors, got {len(docs_data)}'
doctor_names = [d.get('doctor_name') for d in docs_data]
assert '김기중' in doctor_names, '김기중 missing from doctors'
assert '홍길동' in doctor_names, '홍길동 missing from doctors'
assert '김갑순' in doctor_names, '김갑순 missing from doctors'
print(f' [PASS] Multi-Doctor Schema in /api/clinic/info -> {len(docs_data)} doctors verified ({doctor_names})')

# 15. Test Multi-Doctor in /api/clinic/status
r_status_docs = client.get('/api/clinic/status').json()
assert 'doctors' in r_status_docs, 'Missing doctors in /api/clinic/status'
active_docs = r_status_docs['doctors']
assert any(d.get('doctor_name') == '김기중' for d in active_docs)
print(f' [PASS] GET /api/clinic/status doctors -> {len(active_docs)} active doctors')

# 16. Test /api/waiting rooms_summary
r_waiting = client.get('/api/waiting')
assert r_waiting.status_code == 200
wait_json = r_waiting.json()
assert 'doctors' in wait_json, 'Missing doctors in /api/waiting'
assert 'rooms_summary' in wait_json, 'Missing rooms_summary in /api/waiting'
assert '1' in wait_json['rooms_summary'], 'Missing Room 1 in rooms_summary'
assert '2' in wait_json['rooms_summary'], 'Missing Room 2 in rooms_summary'
assert '3' in wait_json['rooms_summary'], 'Missing Room 3 in rooms_summary'
print(' [PASS] GET /api/waiting -> Verified rooms_summary for rooms 1, 2, 3')

# 17. Verify UI components for multi-doctor support
assert '진료실 및 의료진 관리' in client.get('/admin/').text, 'Admin UI missing multi-doctor card'
assert 'kiosk-doc-grid' in client.get('/kiosk/').text, 'Kiosk missing doctor selection grid'
assert 'quick-doctor-card' in client.get('/quick/').text, 'Quick check-in missing doctor selection card'
assert 'room-filter-container' in client.get('/quicklist/').text, 'Quicklist missing room filter container'
assert 'multi-room-mode' in client.get('/signage/style.css').text, 'Signage CSS missing multi-room styles'
print(' [PASS] Multi-doctor UI components in /admin, /kiosk, /quick, /quicklist, /signage verified')

print('\n>>> ALL TEST CASES PASSED SUCCESSFULLY! <<<')
