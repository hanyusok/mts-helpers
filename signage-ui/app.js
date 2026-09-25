document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dateDisplay = document.getElementById('current-date');
    const timeDisplay = document.getElementById('current-time');
    
    const treatingName = document.getElementById('treating-name');
    const treatingRoom = document.getElementById('treating-room');
    
    const nextName = document.getElementById('next-name');
    const nextRoom = document.getElementById('next-room');
    
    const waitingListContainer = document.getElementById('waiting-patients-list');

    // Theme Switcher Controller
    const themeButtons = document.querySelectorAll('.theme-btn');
    const urlParams = new URLSearchParams(window.location.search);
    const urlTheme = urlParams.get('theme');
    let savedTheme = urlTheme || localStorage.getItem('signage_theme') || 'light';
    if (savedTheme === 'dark') {
        savedTheme = 'light';
    }
    
    applyTheme(savedTheme);

    themeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const selectedTheme = btn.getAttribute('data-theme');
            applyTheme(selectedTheme);
            localStorage.setItem('signage_theme', selectedTheme);
        });
    });

    function applyTheme(themeName) {
        let activeTheme = themeName;
        if (activeTheme === 'dark') {
            activeTheme = 'light';
        }
        document.body.className = ''; // Reset
        if (activeTheme !== 'light') {
            document.body.classList.add(`theme-${activeTheme}`);
        }
        
        themeButtons.forEach(btn => {
            if (btn.getAttribute('data-theme') === activeTheme) {
                btn.style.outline = '2px solid #3b82f6';
                btn.style.outlineOffset = '2px';
            } else {
                btn.style.outline = 'none';
            }
        });
    }

    // 1. Digital Clock Updater
    function updateClock() {
        const now = new Date();
        
        // Date formatting: YYYY년 MM월 DD일
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const date = String(now.getDate()).padStart(2, '0');
        
        // Day of week
        const days = ['일', '월', '화', '수', '목', '금', '토'];
        const day = days[now.getDay()];
        
        if (dateDisplay) {
            dateDisplay.textContent = `${year}년 ${month}월 ${date}일 (${day})`;
        }
        
        // Time formatting: HH:mm:ss
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        
        if (timeDisplay) {
            timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }
    
    setInterval(updateClock, 1000);
    updateClock(); // Initial run

    // 2. Name Masking Helper (Privacy compliance)
    function maskName(name) {
        if (!name) return "";
        const len = name.length;
        if (len <= 1) {
            return name;
        } else if (len === 2) {
            return name[0] + "*";
        } else {
            const first = name[0];
            const last = name[len - 1];
            const middle = "*".repeat(len - 2);
            return first + middle + last;
        }
    }

    // 3. Resolve EMR Gateway URL
    let GATEWAY_URL = "";
    if (window.location.protocol === 'file:') {
        GATEWAY_URL = `http://127.0.0.1:${window.GATEWAY_PORT || 3001}`;
    } else if (window.location.port === '3007') {
        GATEWAY_URL = `${window.location.protocol}//${window.location.hostname}:${window.GATEWAY_PORT || 3001}`;
    } else {
        GATEWAY_URL = window.location.origin;
    }

    const signageMain = document.getElementById('signage-main');

    // 4. Fetch and Render EMR Waitlist Data
    async function loadSignageWaitlist() {
        try {
            const res = await fetch(`${GATEWAY_URL}/api/waiting?source=mtsmtr`);
            if (!res.ok) throw new Error("Failed to fetch EMR waitlist data.");
            
            const data = await res.json();
            const queue = data.queue || [];
            
            // Filter out completed treatments if they linger in the array (fin == '*')
            const activeQueue = queue.filter(p => !p.fin || p.fin.trim() !== '*');
            const doctors = (data.doctors && data.doctors.length > 0) ? data.doctors.filter(d => d.active !== false) : [];
            const roomsSummary = data.rooms_summary || {};

            // Update footer legends dynamically
            const legendsContainer = document.querySelector('.room-legends');
            if (legendsContainer) {
                if (doctors.length > 0) {
                    legendsContainer.innerHTML = doctors.map(d => {
                        const code = d.room_code || '1';
                        const roomName = d.room_name || `제${code}진료실`;
                        const docName = d.doctor_name ? ` ${d.doctor_name}` : '';
                        return `<span class="legend-badge badge-room${code}">${roomName}${docName}</span>`;
                    }).join('');
                } else {
                    legendsContainer.innerHTML = '<span class="legend-badge badge-room1">1번 진료실</span>';
                }
            }

            // Decide layout: Multi-Room (>= 2 active doctors) vs Single Room
            if (doctors.length > 1) {
                renderMultiRoomBoard(doctors, roomsSummary, activeQueue);
            } else {
                renderSingleRoomBoard(doctors, activeQueue);
            }
        } catch (err) {
            console.error("Failed to load waitlist for signage:", err);
            if (signageMain) {
                signageMain.innerHTML = `
                    <div class="signage-card" style="grid-column: 1 / -1; justify-content: center; align-items: center; padding: 3rem;">
                        <h2 style="color: #ef4444; margin-bottom: 1rem;"><i class="fa-solid fa-triangle-exclamation"></i> 연결 대기 중</h2>
                        <p style="color: var(--text-muted); font-size: 1.2rem;">대기열 데이터를 불러오는 중입니다. 잠시만 기다려주세요.</p>
                    </div>
                `;
            }
        }
    }

    function renderMultiRoomBoard(doctors, roomsSummary, activeQueue) {
        if (!signageMain) return;
        signageMain.className = 'signage-main multi-room-mode';

        const roomCountClass = `rooms-${Math.min(doctors.length, 3)}`;
        let multiRoomsHtml = `<div class="multi-rooms-grid ${roomCountClass}">`;

        doctors.forEach(doc => {
            const code = doc.room_code || '1';
            const roomName = doc.room_name || `제${code}진료실`;
            const docName = doc.doctor_name || '';
            const docTitle = doc.doctor_title || '원장';

            const rSummary = roomsSummary[code] || { queue: [] };
            const rQueue = (rSummary.queue || []).filter(p => !p.fin || p.fin.trim() !== '*');

            const treating = rQueue.length > 0 ? maskName(rQueue[0].pname || rQueue[0].pcode) : null;
            const next = rQueue.length > 1 ? maskName(rQueue[1].pname || rQueue[1].pcode) : null;
            const waitCount = rQueue.length;

            multiRoomsHtml += `
                <div class="room-station-card room-border-${code}">
                    <div class="room-station-header">
                        <div class="room-station-title">
                            <span class="room-badge-pill badge-room${code}">${roomName}</span>
                            <span class="room-doctor-title">${docName} ${docTitle}</span>
                        </div>
                        <span class="room-wait-pill">대기 ${waitCount}명</span>
                    </div>
                    <div class="room-station-body">
                        <div class="station-box station-box-treating">
                            <div class="station-label">
                                <i class="fa-solid fa-stethoscope"></i> 현재 진료
                            </div>
                            <div class="station-patient ${treating ? '' : 'empty'}">${treating || '진료 준비 중'}</div>
                        </div>
                        <div class="station-box station-box-next">
                            <div class="station-label">
                                <i class="fa-regular fa-clock"></i> 다음 순서
                            </div>
                            <div class="station-patient ${next ? '' : 'empty'}">${next || '대기 없음'}</div>
                        </div>
                    </div>
                </div>
            `;
        });
        multiRoomsHtml += `</div>`;

        // Right side: unified waiting list
        let waitListHtml = `
            <div class="signage-card card-waiting-list">
                <div class="card-header">
                    <h2>대기 고객 (${activeQueue.length}명)</h2>
                </div>
                <div class="card-body">
                    <ul class="waiting-list">
        `;

        if (activeQueue.length > 0) {
            activeQueue.forEach((p, idx) => {
                const waitNum = idx + 1;
                const patientName = maskName(p.pname || p.pcode);
                const roomCode = p.room_code || '1';
                const roomLabel = p.room || `제${roomCode}진료실`;

                waitListHtml += `
                    <li>
                        <div class="patient-item-left">
                            <span class="wait-number">${waitNum}</span>
                            <span>${patientName}</span>
                        </div>
                        <span class="badge-room badge-room${roomCode}">${roomLabel}</span>
                    </li>
                `;
            });
        } else {
            waitListHtml += `<li class="empty-list">대기 중인 고객이 없습니다.</li>`;
        }

        waitListHtml += `
                    </ul>
                </div>
            </div>
        `;

        signageMain.innerHTML = multiRoomsHtml + waitListHtml;
    }

    function renderSingleRoomBoard(doctors, activeQueue) {
        if (!signageMain) return;
        signageMain.className = 'signage-main';

        const doc = doctors.length > 0 ? doctors[0] : { room_name: "제1진료실", doctor_name: "김기중" };
        const roomName = doc.room_name || "제1진료실";

        const treating = activeQueue.length > 0 ? maskName(activeQueue[0].pname || activeQueue[0].pcode) : null;
        const next = activeQueue.length > 1 ? maskName(activeQueue[1].pname || activeQueue[1].pcode) : null;
        const generalQueue = activeQueue.length > 2 ? activeQueue.slice(2) : [];

        let queueItemsHtml = '';
        if (generalQueue.length > 0) {
            queueItemsHtml = generalQueue.map((p, idx) => {
                const waitNum = idx + 1;
                const patientName = maskName(p.pname || p.pcode);
                const roomCode = p.room_code || '1';
                const roomLabel = p.room || roomName;
                return `
                    <li>
                        <div class="patient-item-left">
                            <span class="wait-number">${waitNum}</span>
                            <span>${patientName}</span>
                        </div>
                        <span class="wait-room">${roomLabel}</span>
                    </li>
                `;
            }).join('');
        } else {
            queueItemsHtml = '<li class="empty-list">대기 중인 고객이 없습니다.</li>';
        }

        signageMain.innerHTML = `
            <!-- Column 1: Current Treatment -->
            <div class="signage-card card-treating">
                <div class="card-header">
                    <h2>현재 진료 중</h2>
                </div>
                <div class="card-body">
                    <div class="patient-name ${treating ? '' : 'no-data'}">${treating || '진료 준비 중'}</div>
                    <div class="room-name">${doc.doctor_name ? `${roomName} (${doc.doctor_name})` : roomName}</div>
                </div>
            </div>

            <!-- Column 2: Next Patient -->
            <div class="signage-card card-next">
                <div class="card-header">
                    <h2>다음 고객</h2>
                </div>
                <div class="card-body">
                    <div class="patient-name ${next ? '' : 'no-data'}">${next || '대기 없음'}</div>
                    <div class="room-name">${roomName}</div>
                </div>
            </div>

            <!-- Column 3: Waiting List -->
            <div class="signage-card card-waiting-list">
                <div class="card-header">
                    <h2>대기 고객 (${generalQueue.length}명)</h2>
                </div>
                <div class="card-body">
                    <ul class="waiting-list">
                        ${queueItemsHtml}
                    </ul>
                </div>
            </div>
        `;
    }

    // 5. Establish Real-time WebSocket Connection
    let ws;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl = "";
    if (window.location.protocol === 'file:') {
        wsUrl = `ws://127.0.0.1:${window.GATEWAY_PORT || 3001}/ws/customer`;
    } else if (window.location.port === '3007') {
        wsUrl = `${wsProtocol}//${window.location.hostname}:${window.GATEWAY_PORT || 3001}/ws/customer`;
    } else {
        wsUrl = `${wsProtocol}//${window.location.host}/ws/customer`;
    }

    function connectWebSocket() {
        try {
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log("WebSocket connected successfully for Signage UI.");
                // Fetch initial queue list on connection
                loadSignageWaitlist();
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Refresh if waitlist queue is mutated (added, updated, deleted, or complete)
                    const waitlistMutated = [
                        'WAITING_CREATE', 
                        'WAITING_DELETE', 
                        'WAITING_UPDATE', 
                        'QUEUE_UPDATE'
                    ].includes(data.type);
                    
                    if (waitlistMutated) {
                        console.log("Realtime queue update received. Refreshing waitlist...");
                        loadSignageWaitlist();
                    }
                } catch(e) {
                    console.error("Error parsing websocket JSON message", e);
                }
            };
            
            ws.onclose = () => {
                console.log("WebSocket connection closed. Reconnecting in 3s...");
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = (err) => {
                console.error("WebSocket encountered error:", err);
                ws.close();
            };
        } catch(e) {
            console.error("Failed to connect websocket", e);
        }
    }

    // Initialize Page Data and Connect WS
    connectWebSocket();
});
