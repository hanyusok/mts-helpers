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

    // 4. Fetch and Render EMR Waitlist Data
    async function loadSignageWaitlist() {
        try {
            const res = await fetch(`${GATEWAY_URL}/api/waiting?source=mtsmtr`);
            if (!res.ok) throw new Error("Failed to fetch EMR waitlist data.");
            
            const data = await res.json();
            const queue = data.queue || [];
            
            // Filter out completed treatments if they linger in the array
            // (e.g. FIN == '*' means completed/settled)
            const activeQueue = queue.filter(p => !p.fin || p.fin.trim() !== '*');
            
            // Rendering Column 1: 현재 진료 중 (Currently Treating)
            if (activeQueue.length > 0) {
                const treatingPatient = activeQueue[0];
                treatingName.textContent = maskName(treatingPatient.pname || treatingPatient.pcode);
                treatingName.classList.remove('no-data');
                // Use patient room/gubun if defined, otherwise default to 제1진료실
                treatingRoom.textContent = treatingPatient.room || "1번 진료실";
            } else {
                treatingName.textContent = "진료 준비 중";
                treatingName.classList.add('no-data');
                treatingRoom.textContent = "-";
            }
            
            // Rendering Column 2: 다음 고객 (Next Patient)
            if (activeQueue.length > 1) {
                const nextPatient = activeQueue[1];
                nextName.textContent = maskName(nextPatient.pname || nextPatient.pcode);
                nextName.classList.remove('no-data');
                nextRoom.textContent = nextPatient.room || "1번 진료실";
            } else {
                nextName.textContent = "대기 없음";
                nextName.classList.add('no-data');
                nextRoom.textContent = "-";
            }
            
            // Rendering Column 3: 대기 고객 (Waiting List)
            if (waitingListContainer) {
                waitingListContainer.innerHTML = "";
                
                if (activeQueue.length > 2) {
                    const generalQueue = activeQueue.slice(2);
                    generalQueue.forEach((p, idx) => {
                        const li = document.createElement('li');
                        
                        // Wait number index starts from 1 for the general list (which is actually position 3 onwards)
                        const waitNum = idx + 1;
                        const patientName = maskName(p.pname || p.pcode);
                        const roomLabel = p.room || "1번 진료실";
                        
                        li.innerHTML = `
                            <div class="patient-item-left">
                                <span class="wait-number">${waitNum}</span>
                                <span>${patientName}</span>
                            </div>
                            <span class="wait-room">${roomLabel}</span>
                        `;
                        waitingListContainer.appendChild(li);
                    });
                } else {
                    waitingListContainer.innerHTML = '<li class="empty-list">대기 중인 고객이 없습니다.</li>';
                }
            }
        } catch (err) {
            console.error("Failed to load waitlist for signage:", err);
            treatingName.textContent = "연결 오류";
            nextName.textContent = "연결 오류";
            if (waitingListContainer) {
                waitingListContainer.innerHTML = '<li class="empty-list" style="color:red;">데이터를 가져오지 못했습니다.</li>';
            }
        }
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
