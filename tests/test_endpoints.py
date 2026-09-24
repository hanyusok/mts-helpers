import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 1. Test Root
r_root = client.get('/')
assert r_root.status_code == 200, f'Root failed: {r_root.status_code}'
assert '김기중 소아청소년과의원' in r_root.text, 'Root HTML missing clinic name'
assert '매교역' in r_root.text, 'Root HTML missing station name'
assert 'https://naver.me/GgUzsloE' in r_root.text, 'Root HTML missing naver map url'
print(' [PASS] GET / -> 200 OK (김기중 소아청소년과의원 메인페이지 & 위치 안내)')

# 2. Test /admin
r_admin = client.get('/admin/')
assert r_admin.status_code == 200, f'/admin failed: {r_admin.status_code}'
assert '병원 정보 관리 콘솔' in r_admin.text, 'Admin HTML missing title'
print(' [PASS] GET /admin/ -> 200 OK (병원 정보 관리 콘솔)')

# 3. Test /quick
r_quick = client.get('/quick/')
assert r_quick.status_code == 200, f'/quick failed: {r_quick.status_code}'
print(' [PASS] GET /quick/ -> 200 OK (모바일 간편 접수)')

# 4. Test /quicklist
r_quicklist = client.get('/quicklist/')
assert r_quicklist.status_code == 200, f'/quicklist failed: {r_quicklist.status_code}'
print(' [PASS] GET /quicklist/ -> 200 OK (실시간 대기열)')

# 5. Test /signage
r_signage = client.get('/signage/')
assert r_signage.status_code == 200, f'/signage failed: {r_signage.status_code}'
print(' [PASS] GET /signage/ -> 200 OK (대기실 전광판)')

# 6. Test /config.js
r_config = client.get('/config.js')
assert r_config.status_code == 200, f'/config.js failed: {r_config.status_code}'
assert 'window.GATEWAY_PORT = 3010;' in r_config.text, 'Config JS missing port'
print(' [PASS] GET /config.js -> 200 OK (Port: 3010)')

# 7. Test /api/clinic/info (GET)
r_info = client.get('/api/clinic/info')
assert r_info.status_code == 200, f'/api/clinic/info failed: {r_info.status_code}'
info_data = r_info.json()
assert info_data.get('clinic_name') == '김기중 소아청소년과의원'
assert '매교역' in info_data.get('address')
assert info_data.get('map_url') == 'https://naver.me/GgUzsloE'
print(' [PASS] GET /api/clinic/info -> 200 OK (병원 상세 정보 조회)')

# 8. Test /api/clinic/info (POST edit)
r_edit = client.post('/api/clinic/info', json={'phone': '031-999-8888'})
assert r_edit.status_code == 200, f'/api/clinic/info POST failed: {r_edit.status_code}'
updated_data = client.get('/api/clinic/info').json()
assert updated_data.get('phone') == '031-999-8888'
print(' [PASS] POST /api/clinic/info -> 200 OK (병원 정보 실시간 수정/저장)')

# 9. Test /api/clinic/info/reset
r_reset = client.post('/api/clinic/info/reset')
assert r_reset.status_code == 200
reset_data = client.get('/api/clinic/info').json()
assert reset_data.get('phone') == '031-234-5678'
assert reset_data.get('clinic_name') == '김기중 소아청소년과의원'
print(' [PASS] POST /api/clinic/info/reset -> 200 OK (병원 정보 기본값 복원)')

# 10. Test /api/clinic/status
r_status = client.get('/api/clinic/status')
assert r_status.status_code == 200, f'/api/clinic/status failed: {r_status.status_code}'
data = r_status.json()
assert 'can_checkin' in data, 'Missing can_checkin'
assert data.get('clinic_name') == '김기중 소아청소년과의원'
print(f' [PASS] GET /api/clinic/status -> 200 OK (Clinic: {data.get("clinic_name")}, Status: {data.get("reason")})')

# 11. Test /api/quick/verify validation
r_verify = client.post('/api/quick/verify', json={'pname': '', 'birth': ''})
assert r_verify.status_code == 200
assert r_verify.json()['verified'] is False
print(' [PASS] POST /api/quick/verify -> 200 OK (Graceful validation test)')

print('\n>>> ALL TEST CASES PASSED SUCCESSFULLY! <<<')
