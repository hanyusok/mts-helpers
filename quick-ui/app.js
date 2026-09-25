// Quick Mobile Check-in App Logic

let GATEWAY_URL = "";
if (window.location.protocol === 'file:') {
    GATEWAY_URL = `http://127.0.0.1:${window.GATEWAY_PORT || 3001}`;
} else if (window.location.port === '3007') {
    GATEWAY_URL = `${window.location.protocol}//${window.location.hostname}:${window.GATEWAY_PORT || 3001}`;
} else {
    GATEWAY_URL = window.location.origin;
}

// Current Mode: 'numeric' | 'picker'
let birthMode = 'numeric';
let calculatedIsoBirth = "";
let clinicStatus = null;
let selectedQuickDoc = null;
let selectedQuickRoom = null;
let quickDoctorsList = [];

document.addEventListener("DOMContentLoaded", () => {
    initInputs();
    checkClinicStatus();
    // Re-check status periodically every 30 seconds
    setInterval(checkClinicStatus, 30000);
});

// Check if clinic is open and remote EMR server is alive
async function checkClinicStatus() {
    try {
        const res = await fetch(`${GATEWAY_URL}/api/clinic/status`);
        if (res.ok) {
            clinicStatus = await res.json();
            updateClinicStatusUI(clinicStatus);
        }
    } catch (e) {
        console.warn("[Quick Check-In] Could not check clinic status:", e);
    }
}

function updateClinicStatusUI(status) {
    const banner = document.getElementById("clinic-closed-banner");
    const bannerTitle = document.getElementById("closed-banner-title");
    const bannerDesc = document.getElementById("closed-banner-desc");
    const submitBtn = document.getElementById("submit-btn");
    const modalHours = document.getElementById("modal-hours-text");
    const statusTag = document.getElementById("clinic-status-tag");
    const statusBadgeText = document.getElementById("clinic-status-badge-text");
    const hoursDisplay = document.getElementById("clinic-hours-display");

    if (modalHours && status.clinic_hours_text) {
        modalHours.textContent = status.clinic_hours_text;
    }

    if (hoursDisplay && status.clinic_hours_text) {
        // Extract main operating hours if available
        hoursDisplay.textContent = status.clinic_hours_text.split("(")[0].trim();
    }

    // Render active doctor chips
    if (status.doctors && Array.isArray(status.doctors)) {
        renderQuickDoctorChips(status.doctors);
    }

    // Update clinic-info-card status tag
    if (statusTag && statusBadgeText) {
        if (status.can_checkin) {
            statusTag.className = "clinic-status-tag open";
            statusBadgeText.textContent = "진료 중";
        } else if (status.is_closed_day || (status.message && status.message.includes("휴진"))) {
            statusTag.className = "clinic-status-tag closed";
            statusBadgeText.textContent = "정기 휴진";
        } else if (status.message && status.message.includes("점심시간")) {
            statusTag.className = "clinic-status-tag lunch";
            statusBadgeText.textContent = "점심시간";
        } else {
            statusTag.className = "clinic-status-tag closed";
            statusBadgeText.textContent = status.reason === "SERVER_STOPPED" ? "진료준비중..." : "진료 마감";
        }
    }

    if (!banner) return;

    if (!status.can_checkin) {
        banner.style.display = "flex";
        if (status.is_closed_day || (status.message && status.message.includes("휴진"))) {
            bannerTitle.textContent = "정기 휴진일 안내";
        } else if (status.reason === "SERVER_STOPPED") {
            bannerTitle.textContent = "진료준비중...";
        } else {
            bannerTitle.textContent = "현재 진료시간이 아닙니다";
        }
        bannerDesc.textContent = status.message || "진료시간 외에는 모바일 접수가 불가능합니다.";
    } else {
        banner.style.display = "none";
    }
}

function showClosedModal(customMessage, hoursText) {
    const modal = document.getElementById("clinic-closed-modal");
    const descEl = document.getElementById("modal-closed-desc");
    const hoursEl = document.getElementById("modal-hours-text");

    if (descEl && customMessage) {
        descEl.textContent = customMessage;
    }
    if (hoursEl && hoursText) {
        hoursEl.textContent = hoursText;
    }
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeClosedModal() {
    const modal = document.getElementById("clinic-closed-modal");
    if (modal) {
        modal.style.display = "none";
    }
}

function renderQuickDoctorChips(doctors) {
    const container = document.getElementById("quick-doctor-chips");
    if (!container) return;
    quickDoctorsList = (doctors || []).filter(d => d.active !== false);

    let html = `
        <div class="doctor-chip-card ${selectedQuickRoom === null ? 'selected' : ''}" onclick="selectQuickDoctor(this, null, null)">
            <div class="chip-title"><i class="fa-solid fa-bolt"></i> 빠른 진료</div>
            <div class="chip-sub">대기 적은 진료실 자동 배정</div>
        </div>
    `;

    quickDoctorsList.forEach(d => {
        const isSel = selectedQuickRoom === d.room_code;
        const rNum = d.room_code || 1;
        html += `
            <div class="doctor-chip-card ${isSel ? 'selected' : ''}" onclick="selectQuickDoctor(this, '${d.room_code}', ${d.room_code})">
                <div class="chip-title"><i class="fa-solid fa-user-doctor"></i> ${d.room_name || `제${rNum}진료실`}</div>
                <div class="chip-sub">${d.doctor_name} ${d.doctor_title || '원장'}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function selectQuickDoctor(el, docCode, roomCode) {
    document.querySelectorAll(".doctor-chip-card").forEach(c => c.classList.remove("selected"));
    el.classList.add("selected");
    selectedQuickDoc = docCode;
    selectedQuickRoom = roomCode;
}

function initInputs() {
    const pnameInput = document.getElementById("pname");
    const birthNumericInput = document.getElementById("birth-numeric");
    const birthPickerInput = document.getElementById("pbirth");

    const clearPnameBtn = document.getElementById("clear-pname-btn");
    const clearBirthBtn = document.getElementById("clear-birth-btn");

    // Clear buttons visibility
    pnameInput.addEventListener("input", () => {
        clearPnameBtn.style.display = pnameInput.value.length > 0 ? "flex" : "none";
        hideError();
    });

    birthNumericInput.addEventListener("input", (e) => {
        // Only numbers
        let val = e.target.value.replace(/[^0-9]/g, '');
        if (val.length > 8) val = val.slice(0, 8);
        e.target.value = val;

        clearBirthBtn.style.display = val.length > 0 ? "flex" : "none";
        hideError();
        validateAndFormatBirth(val);
    });

    birthPickerInput.addEventListener("change", (e) => {
        hideError();
        const dateVal = e.target.value; // YYYY-MM-DD
        if (dateVal) {
            calculatedIsoBirth = dateVal;
            const parts = dateVal.split("-");
            updateBirthHelper(true, `${parts[0]}년 ${parts[1]}월 ${parts[2]}일생으로 설정되었습니다.`);
        } else {
            calculatedIsoBirth = "";
            updateBirthHelper(false, "생년월일을 선택해주세요.");
        }
    });
}

function clearField(fieldId) {
    const input = document.getElementById(fieldId);
    if (!input) return;
    input.value = "";
    input.focus();

    if (fieldId === 'pname') {
        document.getElementById("clear-pname-btn").style.display = "none";
    } else if (fieldId === 'birth-numeric') {
        document.getElementById("clear-birth-btn").style.display = "none";
        calculatedIsoBirth = "";
        updateBirthHelper(false, "주민등록번호 앞 6자리(YYMMDD) 또는 8자리를 입력하세요.");
    }
}

// Toggle between 6-digit numeric keypad and date picker
function toggleBirthInputMode() {
    const numGroup = document.getElementById("numeric-input-group");
    const pickerGroup = document.getElementById("date-picker-group");
    const toggleLabel = document.getElementById("toggle-picker-label");
    const birthNumeric = document.getElementById("birth-numeric");
    const birthPicker = document.getElementById("pbirth");

    if (birthMode === 'numeric') {
        birthMode = 'picker';
        numGroup.style.display = 'none';
        pickerGroup.style.display = 'flex';
        toggleLabel.textContent = "숫자키로 입력";
        
        // If we already have calculated ISO birth, prefill picker
        if (calculatedIsoBirth) {
            birthPicker.value = calculatedIsoBirth;
        }
        birthPicker.focus();
    } else {
        birthMode = 'numeric';
        pickerGroup.style.display = 'none';
        numGroup.style.display = 'flex';
        toggleLabel.textContent = "달력으로 선택";

        if (birthPicker.value) {
            const clean = birthPicker.value.replace(/-/g, '');
            birthNumeric.value = clean;
            validateAndFormatBirth(clean);
        }
        birthNumeric.focus();
    }
}

// Smart birthdate parser for Korean clinic registration
function validateAndFormatBirth(raw) {
    if (!raw || (raw.length !== 6 && raw.length !== 8)) {
        calculatedIsoBirth = "";
        updateBirthHelper(false, raw.length > 0 ? `${raw.length}자리 입력 중... (6자리 또는 8자리 입력)` : "주민등록번호 앞 6자리(YYMMDD) 또는 8자리를 입력하세요.");
        return;
    }

    let year, month, day;
    const currentYear = new Date().getFullYear();

    if (raw.length === 6) {
        let yy = parseInt(raw.slice(0, 2), 10);
        month = raw.slice(2, 4);
        day = raw.slice(4, 6);

        // 2-digit year inference: e.g. 00~26 -> 2000s, 27~99 -> 1900s
        const cutoff = currentYear % 100;
        year = yy <= cutoff ? (2000 + yy) : (1900 + yy);
    } else if (raw.length === 8) {
        year = parseInt(raw.slice(0, 4), 10);
        month = raw.slice(4, 6);
        day = raw.slice(6, 8);
    }

    const mNum = parseInt(month, 10);
    const dNum = parseInt(day, 10);

    // Validate date parts
    if (mNum < 1 || mNum > 12 || dNum < 1 || dNum > 31 || year < 1900 || year > currentYear) {
        calculatedIsoBirth = "";
        updateBirthHelper(false, "올바르지 않은 생년월일입니다. 다시 확인해 주세요.", true);
        return;
    }

    const iso = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    calculatedIsoBirth = iso;
    updateBirthHelper(true, `✓ ${year}년 ${mNum}월 ${dNum}일 (${iso})`);
}

function updateBirthHelper(isValid, text, isError = false) {
    const helper = document.getElementById("birth-helper");
    const helperText = document.getElementById("birth-helper-text");
    helperText.textContent = text;

    if (isValid) {
        helper.className = "helper-box valid";
        helper.querySelector("i").className = "fa-solid fa-circle-check";
    } else if (isError) {
        helper.className = "helper-box";
        helper.style.color = "var(--danger)";
        helper.querySelector("i").className = "fa-solid fa-circle-exclamation";
        helper.querySelector("i").style.color = "var(--danger)";
    } else {
        helper.className = "helper-box";
        helper.style.color = "";
        helper.querySelector("i").className = "fa-solid fa-circle-info";
        helper.querySelector("i").style.color = "var(--primary)";
    }
}

function showError(msg) {
    const banner = document.getElementById("error-banner");
    const msgEl = document.getElementById("error-message");
    msgEl.textContent = msg;
    banner.style.display = "flex";
    banner.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideError() {
    const banner = document.getElementById("error-banner");
    if (banner) banner.style.display = "none";
}

function showToast(msg) {
    const toast = document.getElementById("toast");
    const toastText = document.getElementById("toast-text");
    toastText.textContent = msg;
    toast.style.display = "block";
    setTimeout(() => {
        toast.style.display = "none";
    }, 3000);
}

// Main check-in handler
async function handleFormSubmit(event) {
    event.preventDefault();
    hideError();

    // Check clinic hours / server status upfront
    if (clinicStatus && !clinicStatus.can_checkin) {
        showClosedModal(clinicStatus.message, clinicStatus.clinic_hours_text);
        return;
    }

    const pname = document.getElementById("pname").value.trim();
    const submitBtn = document.getElementById("submit-btn");
    const spinner = document.getElementById("btn-spinner");
    const btnText = submitBtn.querySelector(".btn-text");
    const arrowIcon = submitBtn.querySelector(".fa-arrow-right-long");

    if (!pname) {
        showError("환자 성명을 입력해주세요.");
        document.getElementById("pname").focus();
        return;
    }

    if (!calculatedIsoBirth) {
        showError("정확한 생년월일을 입력해 주세요.");
        if (birthMode === 'numeric') {
            document.getElementById("birth-numeric").focus();
        } else {
            document.getElementById("pbirth").focus();
        }
        return;
    }

    const pbirth = calculatedIsoBirth; // Format: YYYY-MM-DD

    // Loading UI state
    submitBtn.disabled = true;
    spinner.style.display = "block";
    arrowIcon.style.display = "none";
    btnText.textContent = "환자 조회 및 접수 중...";

    // 4-second timeout to prevent indefinite hanging if remote server is stopped
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 4000);

    try {
        // Step 1: Verify patient identity via secure /api/quick/verify
        const verifyUrl = `${GATEWAY_URL}/api/quick/verify`;
        let resVerify;

        try {
            resVerify = await fetch(verifyUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pname: pname, pbirth: pbirth }),
                signal: abortController.signal
            });
        } catch (fetchErr) {
            clearTimeout(timeoutId);
            if (fetchErr.name === 'AbortError' || fetchErr.message?.includes('Failed to fetch')) {
                showClosedModal("현재 진료시간이 아니거나 진료준비중입니다. 진료시간 내에 접수해 주세요.");
                throw new Error("현재 진료시간이 아니거나 진료준비중입니다.");
            }
            throw fetchErr;
        }

        clearTimeout(timeoutId);

        if (!resVerify.ok) {
            let errorDetail = "진료 접수 처리에 실패했습니다. 데스크에 문의해 주세요.";
            try {
                const errData = await resVerify.json();
                if (errData && errData.detail) errorDetail = errData.detail;
            } catch (_) {}

            if (resVerify.status === 503 || errorDetail.includes("진료시간") || errorDetail.includes("준비중") || errorDetail.includes("서버")) {
                showClosedModal(errorDetail);
                throw new Error(errorDetail);
            }
            throw new Error(errorDetail);
        }

        const verifyData = await resVerify.json();
        if (!verifyData.verified || !verifyData.pcode) {
            throw new Error(verifyData.message || "등록된 환자 정보를 찾을 수 없습니다. 처음 오신 분은 접수처 데스크에 문의해 주세요.");
        }

        const pcode = verifyData.pcode;
        console.log(`[Quick Check-In] Patient verified: ${pname} (Chart #: ${pcode})`);

        // Step 2: Register on MTSMTR waiting ledger
        const registerUrl = `${GATEWAY_URL}/api/mtr`;
        const payload = {
            pcode: pcode,
            pname: pname,
            pbirth: pbirth,
            gubun: "모바일", // Marked as mobile check-in
            doc: selectedQuickDoc || (selectedQuickRoom ? String(selectedQuickRoom) : null),
            room_code: selectedQuickRoom
        };

        const resRegister = await fetch(registerUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!resRegister.ok) {
            let errorDetail = "대기 접수 처리에 실패했습니다.";
            try {
                const errJson = await resRegister.json();
                if (errJson && errJson.detail) errorDetail = errJson.detail;
            } catch (_) {}

            if (resRegister.status === 503 || errorDetail.includes("진료시간") || errorDetail.includes("준비중") || errorDetail.includes("서버")) {
                showClosedModal(errorDetail);
            }
            throw new Error(errorDetail);
        }

        const regResult = await resRegister.json();
        console.log("[Quick Check-In] Success:", regResult);

        // Step 3: Show Success View (Ticket Style)
        displaySuccessTicket(pname, pbirth, regResult);

    } catch (err) {
        console.error("[Quick Check-In Error]", err);
        showError(err.message || "오류가 발생했습니다. 진료시간 및 데스크를 확인해주세요.");
        showToast(err.message || "접수 실패");
    } finally {
        submitBtn.disabled = false;
        spinner.style.display = "none";
        arrowIcon.style.display = "inline-block";
        btnText.textContent = "진료 접수하기";
    }
}

let redirectTimer = null;

function cancelAutoRedirect() {
    if (redirectTimer) {
        clearInterval(redirectTimer);
        redirectTimer = null;
    }
    const btnText = document.getElementById("btn-go-quicklist-text");
    if (btnText) {
        btnText.textContent = "내 대기시간 실시간 조회";
    }
}

function displaySuccessTicket(pname, pbirth, regResult) {
    // Store in localStorage for /quicklist personalization
    try {
        localStorage.setItem('quick_patient_name', pname);
        localStorage.setItem('quick_patient_birth', pbirth);
        if (regResult && regResult.resid1) {
            localStorage.setItem('quick_patient_resid1', regResult.resid1);
        }
        if (regResult && regResult.room_code) {
            localStorage.setItem('quick_patient_room_code', String(regResult.room_code));
            localStorage.setItem('quick_patient_room_name', regResult.room_name || '');
        }
    } catch (e) {
        console.warn("Could not save patient to localStorage", e);
    }

    document.getElementById("form-view").style.display = "none";
    const successView = document.getElementById("success-view");
    successView.style.display = "flex";

    // Bind data
    document.getElementById("res-patient-name").textContent = pname;
    document.getElementById("res-patient-birth").textContent = pbirth;

    const assignedRoomText = regResult && regResult.room_name 
        ? `${regResult.room_name} (${regResult.doctor_name || ''} 원장)`
        : "제1진료실 (김기중 대표원장)";
    const resRoomEl = document.getElementById("res-assigned-room");
    if (resRoomEl) resRoomEl.textContent = assignedRoomText;

    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    const dateStr = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}-${now.getDate().toString().padStart(2, '0')}`;
    document.getElementById("res-register-time").textContent = `${dateStr} ${timeStr}`;

    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Directly navigate to /quicklist/ after 2 seconds countdown
    let countdown = 2;
    const btnText = document.getElementById("btn-go-quicklist-text");
    if (btnText) {
        btnText.textContent = `내 대기시간 실시간 조회 (${countdown}초 후 자동 이동)`;
    }

    if (redirectTimer) clearInterval(redirectTimer);
    redirectTimer = setInterval(() => {
        countdown--;
        if (countdown > 0) {
            if (btnText) btnText.textContent = `내 대기시간 실시간 조회 (${countdown}초 후 자동 이동)`;
        } else {
            clearInterval(redirectTimer);
            redirectTimer = null;
            window.location.href = "/quicklist/";
        }
    }, 1000);
}

function resetForm() {
    cancelAutoRedirect();
    document.getElementById("quick-checkin-form").reset();
    clearField('pname');
    clearField('birth-numeric');
    calculatedIsoBirth = "";
    selectedQuickDoc = null;
    selectedQuickRoom = null;
    renderQuickDoctorChips(quickDoctorsList);
    hideError();

    // Reset views
    document.getElementById("success-view").style.display = "none";
    const formView = document.getElementById("form-view");
    formView.style.display = "flex";

    updateBirthHelper(false, "주민등록번호 앞 6자리(YYMMDD) 또는 8자리를 입력하세요.");
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
