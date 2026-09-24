// QuickList Mobile Waitlist App Logic

let GATEWAY_URL = "";
if (window.location.protocol === 'file:') {
    GATEWAY_URL = `http://127.0.0.1:${window.GATEWAY_PORT || 3010}`;
} else if (window.location.port === '3007') {
    GATEWAY_URL = `${window.location.protocol}//${window.location.hostname}:${window.GATEWAY_PORT || 3010}`;
} else {
    GATEWAY_URL = window.location.origin;
}

// Stored patient name from /quick/ registration
let myStoredName = localStorage.getItem('quick_patient_name') || "";
let myStoredBirth = localStorage.getItem('quick_patient_birth') || "";
let myStoredResid1 = localStorage.getItem('quick_patient_resid1') || "";

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initMyWaitBanner();
    loadWaitlistData();
    initWebSocket();

    // Auto-polling fallback (every 10 seconds in case websocket drops or mobile sleeps)
    setInterval(() => {
        loadWaitlistData(true);
    }, 10000);
});

// 1. Digital Clock
function initClock() {
    const dateEl = document.getElementById('current-date');
    const timeEl = document.getElementById('current-time');

    function updateClock() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const date = String(now.getDate()).padStart(2, '0');
        const days = ['일', '월', '화', '수', '목', '금', '토'];
        const day = days[now.getDay()];

        if (dateEl) {
            dateEl.textContent = `${year}년 ${month}월 ${date}일 (${day})`;
        }

        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');

        if (timeEl) {
            timeEl.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }

    setInterval(updateClock, 1000);
    updateClock();
}

// 2. Name Masking Helper (Privacy Compliance)
function maskName(name) {
    if (!name) return "";
    const str = String(name).trim();
    const len = str.length;
    if (len <= 1) return str;
    if (len === 2) return str[0] + "*";
    
    const first = str[0];
    const last = str[len - 1];
    const middle = "*".repeat(len - 2);
    return first + middle + last;
}

// 3. Personalized My Wait Banner
function initMyWaitBanner() {
    const banner = document.getElementById('my-wait-banner');
    const nameEl = document.getElementById('my-patient-name');
    if (!myStoredName) {
        banner.style.display = 'none';
        return;
    }
    nameEl.textContent = myStoredName;
    banner.style.display = 'block';
}

function clearMyPatient() {
    localStorage.removeItem('quick_patient_name');
    localStorage.removeItem('quick_patient_birth');
    localStorage.removeItem('quick_patient_resid1');
    myStoredName = "";
    myStoredBirth = "";
    myStoredResid1 = "";
    document.getElementById('my-wait-banner').style.display = 'none';
    showToast("내 환자 정보 연결이 해제되었습니다.");
    loadWaitlistData(true);
}

// 4. Fetch and Render Waitlist Data
async function loadWaitlistData(silent = false) {
    const treatingName = document.getElementById('treating-name');
    const treatingRoom = document.getElementById('treating-room');
    const treatingSub = document.getElementById('treating-sub');

    const nextName = document.getElementById('next-name');
    const nextRoom = document.getElementById('next-room');
    const nextSub = document.getElementById('next-sub');

    const countTreating = document.getElementById('count-treating');
    const countWaiting = document.getElementById('count-waiting');
    const listTotalBadge = document.getElementById('list-total-badge');
    const listContainer = document.getElementById('waiting-patients-list');
    const closedBanner = document.getElementById('clinic-closed-banner');
    const closedBannerText = document.getElementById('closed-banner-text');

    // 4-1. Check Clinic Operating & Server Status first
    try {
        const statusRes = await fetch(`${GATEWAY_URL}/api/clinic/status`);
        if (statusRes.ok) {
            const status = await statusRes.json();
            if (!status.can_checkin) {
                if (closedBanner) {
                    closedBanner.style.display = 'flex';
                    if (closedBannerText) {
                        closedBannerText.textContent = `${status.message} (${status.clinic_hours_text})`;
                    }
                }
                if (!status.server_alive || !status.is_open) {
                    treatingName.textContent = "진료 마감";
                    treatingName.classList.add('no-data');
                    treatingRoom.textContent = "-";
                    treatingSub.textContent = status.message;

                    nextName.textContent = "-";
                    nextName.classList.add('no-data');
                    nextRoom.textContent = "-";
                    nextSub.textContent = "진료시간 외 운영 종료";

                    countTreating.textContent = "0명";
                    countWaiting.textContent = "0명";
                    listTotalBadge.textContent = "대기 0명";

                    if (listContainer) {
                        listContainer.innerHTML = `
                            <li class="empty-item">
                                <i class="fa-solid fa-business-time" style="font-size:1.8rem; color:var(--accent);"></i>
                                <strong style="color:var(--text-main); margin-top:0.25rem;">현재 진료시간이 아닙니다</strong>
                                <span style="font-size:0.8rem; color:var(--text-muted);">${status.clinic_hours_text || '진료시간: 10:00 ~ 18:00 (매주 화·수요일 휴진, 토·일 주말 정상진료)'}</span>
                            </li>
                        `;
                    }
                    return;
                }
            } else {
                if (closedBanner) closedBanner.style.display = 'none';
            }
        }
    } catch (e) {
        console.warn("[QuickList] Clinic status check bypassed:", e);
    }

    try {
        const res = await fetch(`${GATEWAY_URL}/api/waiting?source=mtsmtr`);
        if (!res.ok) {
            if (res.status === 503) {
                const errData = await res.json().catch(() => ({}));
                if (closedBanner) {
                    closedBanner.style.display = 'flex';
                    if (closedBannerText) {
                        closedBannerText.textContent = errData.detail || "현재 진료시간이 아니거나 진료준비중입니다.";
                    }
                }
                treatingName.textContent = "진료준비중...";
                treatingName.classList.add('no-data');
                treatingSub.textContent = "현재 진료시간이 아니거나 진료준비중입니다.";
                return;
            }
            throw new Error("대기 정보를 불러올 수 없습니다.");
        }

        if (closedBanner) closedBanner.style.display = 'none';

        const data = await res.json();
        const queue = data.queue || [];

        // Filter active patients (exclude finished treatments marked with '*')
        const activeQueue = queue.filter(p => !p.fin || p.fin.trim() !== '*');

        // Update Counter Badges
        const isTreating = activeQueue.length > 0;
        countTreating.textContent = isTreating ? "1명" : "0명";
        countWaiting.textContent = `${activeQueue.length}명`;
        listTotalBadge.textContent = `대기 ${Math.max(0, activeQueue.length - 2)}명`;

        // Spot 1: Currently Treating (activeQueue[0])
        if (activeQueue.length > 0) {
            const p0 = activeQueue[0];
            treatingName.textContent = maskName(p0.pname || p0.pcode);
            treatingName.classList.remove('no-data');
            treatingRoom.textContent = p0.room || "1번 진료실";
            treatingSub.textContent = "진료실에서 진료 진행 중";
        } else {
            treatingName.textContent = "진료 준비 중";
            treatingName.classList.add('no-data');
            treatingRoom.textContent = "-";
            treatingSub.textContent = "현재 진료 대기 중인 환자가 없습니다";
        }

        // Spot 2: Next Patient (activeQueue[1])
        if (activeQueue.length > 1) {
            const p1 = activeQueue[1];
            nextName.textContent = maskName(p1.pname || p1.pcode);
            nextName.classList.remove('no-data');
            nextRoom.textContent = p1.room || "1번 진료실";
            nextSub.textContent = "진료실 입장을 준비해 주세요";
        } else {
            nextName.textContent = "대기 없음";
            nextName.classList.add('no-data');
            nextRoom.textContent = "-";
            nextSub.textContent = "다음 대기 환자가 없습니다";
        }

        // Spot 3: General Waiting List (Position 3 onwards)
        if (listContainer) {
            listContainer.innerHTML = "";

            if (activeQueue.length > 2) {
                const restQueue = activeQueue.slice(2);
                restQueue.forEach((p, idx) => {
                    const waitNum = idx + 1; // 1, 2, 3...
                    const realIndex = idx + 2; // actual queue position 3, 4, 5...
                    const pName = p.pname || String(p.pcode);
                    const isMyPatient = isSamePatient(pName, p.pbirth, p.resid1);

                    const li = document.createElement('li');
                    li.className = `waiting-item ${isMyPatient ? 'is-my-turn' : ''}`;

                    const timeStr = p.visitime ? p.visitime.slice(0, 5) : '';

                    li.innerHTML = `
                        <div class="item-left">
                            <span class="order-badge">${waitNum}</span>
                            <span class="item-name">${maskName(pName)}${isMyPatient ? '<span class="my-tag">내 순서</span>' : ''}</span>
                        </div>
                        <div class="item-right">
                            <span class="item-room">${p.room || '1번 진료실'}</span>
                            ${timeStr ? `<span class="item-time">${timeStr}</span>` : ''}
                        </div>
                    `;
                    listContainer.appendChild(li);
                });
            } else {
                listContainer.innerHTML = `
                    <li class="empty-item">
                        <i class="fa-regular fa-clipboard" style="font-size:1.8rem; color:var(--text-sub);"></i>
                        <span>현재 대기 중인 고객이 없습니다.</span>
                    </li>
                `;
            }
        }

        // Update Personalized My Wait Banner
        updateMyWaitStatus(activeQueue);

    } catch (err) {
        console.error("[QuickList] Fetch error:", err);
        if (!silent) {
            showToast("대기열 정보를 갱신하지 못했습니다.");
        }
    }
}

function isSamePatient(name, birth, resid1) {
    if (myStoredResid1 && resid1 && myStoredResid1 === resid1) return true;
    if (!myStoredName) return false;
    const maskedStored = maskName(myStoredName);
    const targetName = (name || '').trim();
    const nameMatch = (myStoredName.trim() === targetName) || (maskedStored === targetName);
    if (myStoredBirth && birth) {
        return nameMatch && (myStoredBirth === birth);
    }
    return nameMatch;
}

function updateMyWaitStatus(activeQueue) {
    const banner = document.getElementById('my-wait-banner');
    if (!myStoredName || !banner) return;

    // Find position of my patient in activeQueue
    const myIdx = activeQueue.findIndex(p => isSamePatient(p.pname, p.pbirth, p.resid1));
    const posEl = document.getElementById('my-queue-pos');
    const aheadEl = document.getElementById('my-ahead-count');
    const hintEl = document.getElementById('my-status-hint');

    if (myIdx === -1) {
        // Not found in active queue (either completed, cancelled, or not yet synced)
        banner.style.display = 'block';
        posEl.textContent = "진료 완료 / 미등록";
        posEl.style.fontSize = "1rem";
        aheadEl.textContent = "-";
        hintEl.textContent = "현재 대기 명단에 없습니다. 접수처 또는 간편접수를 확인해 주세요.";
    } else if (myIdx === 0) {
        // Currently treating
        banner.style.display = 'block';
        posEl.textContent = "현재 진료 중!";
        posEl.style.fontSize = "1.2rem";
        posEl.className = "my-stat-value primary";
        aheadEl.textContent = "0명 (입장)";
        hintEl.innerHTML = `<strong>${myStoredName}</strong>님, 진료실로 입장해 주세요!`;
    } else if (myIdx === 1) {
        // Next in line
        banner.style.display = 'block';
        posEl.textContent = "다음 순서 (1번째)";
        posEl.style.fontSize = "1.2rem";
        posEl.className = "my-stat-value primary";
        aheadEl.textContent = "0명 (곧 입장)";
        hintEl.innerHTML = `다음 차례입니다. 진료실 문 앞 대기실에서 잠시만 기다려 주세요.`;
    } else {
        // Position 3 or later
        banner.style.display = 'block';
        posEl.textContent = `${myIdx + 1}번째`;
        posEl.style.fontSize = "1.35rem";
        posEl.className = "my-stat-value";
        aheadEl.textContent = `${myIdx}명`;
        hintEl.textContent = `순서가 가까워지면 원내 대기실에서 대기해 주세요.`;
    }
}

// 5. WebSocket Real-time Updates
let ws;
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
let wsUrl = "";
if (window.location.protocol === 'file:') {
    wsUrl = `ws://127.0.0.1:${window.GATEWAY_PORT || 3010}/ws/customer`;
} else if (window.location.port === '3007') {
    wsUrl = `${wsProtocol}//${window.location.hostname}:${window.GATEWAY_PORT || 3010}/ws/customer`;
} else {
    wsUrl = `${wsProtocol}//${window.location.host}/ws/customer`;
}

function initWebSocket() {
    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("[QuickList] WebSocket connected.");
            loadWaitlistData(true);
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                const isQueueMutation = [
                    'WAITING_CREATE',
                    'WAITING_DELETE',
                    'WAITING_UPDATE',
                    'QUEUE_UPDATE'
                ].includes(msg.type);

                if (isQueueMutation) {
                    console.log("[QuickList] Realtime queue update received:", msg.type);
                    loadWaitlistData(true);
                }
            } catch (e) {
                console.error("[QuickList] Error parsing WS message", e);
            }
        };

        ws.onclose = () => {
            console.log("[QuickList] WebSocket disconnected. Reconnecting in 3s...");
            setTimeout(initWebSocket, 3000);
        };

        ws.onerror = (err) => {
            console.error("[QuickList] WebSocket error:", err);
            ws.close();
        };
    } catch (e) {
        console.error("[QuickList] Failed to initialize WebSocket:", e);
    }
}

function manualRefresh() {
    const btn = document.getElementById('btn-refresh');
    btn.style.transform = 'rotate(360deg)';
    setTimeout(() => { btn.style.transform = ''; }, 400);
    loadWaitlistData();
    showToast("대기열을 새로고침했습니다.");
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    const toastText = document.getElementById('toast-text');
    toastText.textContent = msg;
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 2500);
}
