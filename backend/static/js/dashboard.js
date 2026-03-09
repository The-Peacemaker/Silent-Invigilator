/**
 * THE SILENT INVIGILATOR — Dashboard Controller
 * Matches SDD Module Design: GUI & Visualization Module
 * Drives all real-time display from /status API endpoint
 */

/* ── CLOCK ──────────────────────────────────────────────── */
function updateClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('clock-display').textContent = `${h}:${m}:${s}`;
}
setInterval(updateClock, 1000);
updateClock();

/* ── ANOMALY CHART (SDD — Temporal Filtering Module output) ─ */
const chartCtx = document.getElementById('anomalyChart').getContext('2d');
const HISTORY_LEN = 30;
const chartData = Array(HISTORY_LEN).fill(0);
const chartLabels = Array(HISTORY_LEN).fill('');

Chart.defaults.font.family = "'Special Elite', cursive";
Chart.defaults.color = '#4a4a6a';

const anomalyChart = new Chart(chartCtx, {
    type: 'line',
    data: {
        labels: chartLabels,
        datasets: [{
            label: 'Anomaly Score',
            data: chartData,
            borderColor: '#1a1a2e',
            backgroundColor: 'rgba(26,26,46,0.08)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: '#1a1a2e',
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(0,0,0,0.05)' },
                ticks: { stepSize: 25, font: { size: 9 } },
                border: { dash: [3, 3] }
            },
            x: { display: false }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: ctx => ` Score: ${ctx.raw}`
                }
            }
        }
    }
});

/* ── STATE ──────────────────────────────────────────────── */
let sessionAlertCount = 0;
let lastAlertTs = 0;
const ALERT_COOLDOWN = 2500; // ms
let isPolling = false;

/* ── HELPERS ────────────────────────────────────────────── */

/**
 * Classify risk score into SDD-specified color tier
 * Green  < 30  | Orange < 70  | Red >= 70
 */
function getRiskTier(score) {
    if (score < 30) return { label: 'LOW RISK', color: '#2d8a4e', css: 'var(--focused)' };
    if (score < 70) return { label: 'SUSPICIOUS', color: '#b5600a', css: 'var(--alert)' };
    return { label: 'HIGH RISK', color: '#c0392b', css: 'var(--danger)' };
}

/**
 * Apply SDD color-coding to a status item element
 * green = focused, yellow = looking L/R, orange = up/down, red = suspicious/phone
 */
function applyStatusClass(el, level) {
    el.classList.remove('si-focused', 'si-warn', 'si-alert', 'si-danger');
    if (level === 'ok') el.classList.add('si-focused');
    if (level === 'warn') el.classList.add('si-warn');
    if (level === 'alert') el.classList.add('si-alert');
    if (level === 'danger') el.classList.add('si-danger');
}

/**
 * Push an entry to the alert log panel (SDD — Alert & Notification Module)
 */
function logAlert(msg, type = 'warn') {
    const now = Date.now();
    if (now - lastAlertTs < ALERT_COOLDOWN) return;
    lastAlertTs = now;
    sessionAlertCount++;
    document.getElementById('met-alerts').textContent = sessionAlertCount;

    const log = document.getElementById('alert-log');

    // clear the placeholder
    const placeholder = log.querySelector('.no-alerts');
    if (placeholder) placeholder.remove();

    const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
    const entry = document.createElement('div');
    entry.className = `alert-entry ae-${type}`;
    entry.innerHTML = `<span class="ae-time">${time}</span><span class="ae-msg">${msg}</span>`;
    log.prepend(entry);

    // keep only 20 entries
    while (log.children.length > 20) log.lastChild.remove();
}

function clearAlerts() {
    document.getElementById('alert-log').innerHTML =
        '<div class="no-alerts">Log cleared ✓</div>';
}

/**
 * Map the normalized pose bar fill (0-100%) from angle
 * angle range ±45 → map to 0-100% with 50% = center
 */
function poseAngleToPercent(angle) {
    const clamped = Math.max(-45, Math.min(45, angle));
    return ((clamped + 45) / 90) * 100;
}

/* ── MAIN POLL LOOP ─────────────────────────────────────── */
function pollStatus() {
    if (isPolling) return;
    isPolling = true;

    fetch('/status')
        .then(r => r.json())
        .then(data => {
            isPolling = false;
            updateDashboard(data);
        })
        .catch(() => {
            isPolling = false;
            // Mark connection offline
            const pill = document.getElementById('conn-pill');
            pill.textContent = '⬤ OFFLINE';
            pill.classList.remove('live');
            pill.classList.add('offline');
        });
}

function updateDashboard(data) {
    /* ── CONNECTION STATUS ───────────── */
    const pill = document.getElementById('conn-pill');
    pill.textContent = '⬤ LIVE';
    pill.classList.add('live');
    pill.classList.remove('offline');

    /* ── RISK SCORE ──────────────────── */
    const score = Math.round(data.risk_score || 0);
    const tier = getRiskTier(score);

    document.getElementById('risk-number').textContent = String(score).padStart(2, '0');
    document.getElementById('risk-number').style.color = tier.color;
    document.getElementById('risk-level-text').textContent = tier.label;
    document.getElementById('risk-level-text').style.color = tier.color;

    const bar = document.getElementById('risk-bar');
    bar.style.width = `${score}%`;
    bar.style.background = tier.color;

    /* ── CHART UPDATE ────────────────── */
    anomalyChart.data.datasets[0].data.shift();
    anomalyChart.data.datasets[0].data.push(score);
    // update border color for current tier
    anomalyChart.data.datasets[0].borderColor = tier.color;
    anomalyChart.data.datasets[0].backgroundColor = tier.color + '18';
    anomalyChart.update('none');

    /* ── STATUS INDICATORS (SDD 7.1 color scheme) ── */

    // Face
    const faceEl = document.getElementById('si-face');
    const faceVal = document.getElementById('si-face-val');
    if (data.face_detected) {
        faceVal.textContent = 'Detected ✓';
        applyStatusClass(faceEl, 'ok');
    } else {
        faceVal.textContent = 'Not Found ✗';
        applyStatusClass(faceEl, 'danger');
        logAlert('⚠ No face detected — student may be absent', 'danger');
    }

    // Head Pose
    const poseEl = document.getElementById('si-pose');
    const poseVal = document.getElementById('si-pose-val');
    const pose = data.head_pose || 'Center';
    poseVal.textContent = pose;
    if (pose === 'Center') {
        applyStatusClass(poseEl, 'ok');
    } else if (pose.includes('Up') || pose.includes('Down')) {
        applyStatusClass(poseEl, 'alert');  // orange per SDD
    } else {
        applyStatusClass(poseEl, 'warn');   // yellow per SDD
    }

    // Gaze
    const gazeEl = document.getElementById('si-gaze');
    const gazeVal = document.getElementById('si-gaze-val');
    const gaze = data.gaze || 'Center';
    gazeVal.textContent = gaze === 'Center' ? 'Focused ✓' : `Gaze: ${gaze}`;
    applyStatusClass(gazeEl, gaze === 'Center' ? 'ok' : 'warn');

    // Phone / Object Det.
    const phoneEl = document.getElementById('si-phone');
    const phoneVal = document.getElementById('si-phone-val');
    if (data.phone_detected) {
        phoneVal.textContent = 'PHONE DETECTED';
        applyStatusClass(phoneEl, 'danger');
        logAlert('🚨 Mobile phone detected in frame!', 'danger');
    } else {
        phoneVal.textContent = 'None ✓';
        applyStatusClass(phoneEl, 'ok');
    }

    /* ── BEHAVIORAL STATE (SDD Output) ─ */
    const stateEl = document.getElementById('behavior-state');
    const detections = data.detections || [];

    let stateText = '✓ Focused';
    let stateColor = 'var(--focused)';
    let stateBg = 'var(--focused-bg)';

    if (score >= 70 || data.phone_detected) {
        stateText = '⚠ SUSPICIOUS BEHAVIOR';
        stateColor = 'var(--danger)';
        stateBg = 'var(--danger-bg)';
    } else if (detections.some(d => d.toLowerCase().includes('down') || d.toLowerCase().includes('up'))) {
        stateText = '↕ Looking ' + (detections.find(d => d.toLowerCase().includes('down') || d.toLowerCase().includes('up')) || '');
        stateColor = 'var(--alert)';
        stateBg = 'var(--alert-bg)';
    } else if (pose !== 'Center' || gaze !== 'Center') {
        stateText = '↔ Looking Away';
        stateColor = 'var(--warn)';
        stateBg = 'var(--warn-bg)';
    }

    stateEl.textContent = stateText;
    stateEl.style.color = stateColor;
    stateEl.parentElement.style.background = stateBg;
    stateEl.parentElement.style.borderColor = stateColor;

    /* ── METRICS BAR ─────────────────── */
    document.getElementById('met-gaze').textContent = gaze;
    document.getElementById('met-pose').textContent = pose;

    // Parse numerical yaw / pitch if returned by backend
    // (backend can add these to /status response later; use 0 as placeholder)
    const yaw = typeof data.yaw === 'number' ? data.yaw : 0;
    const pitch = typeof data.pitch === 'number' ? data.pitch : 0;

    document.getElementById('met-yaw').textContent = `${yaw.toFixed(1)}°`;
    document.getElementById('met-pitch').textContent = `${pitch.toFixed(1)}°`;

    // Persons count (from detections list)
    const personMatch = detections.find(d => d.toLowerCase().includes('student'));
    if (personMatch) {
        const numMatch = personMatch.match(/\d+/);
        if (numMatch) document.getElementById('met-persons').textContent = numMatch[0];
    }

    /* ── HEAD POSE BARS ─────────────── */
    document.getElementById('pv-yaw').textContent = `${yaw.toFixed(1)}°`;
    document.getElementById('pv-pitch').textContent = `${pitch.toFixed(1)}°`;
    document.getElementById('pb-yaw').style.width = `${poseAngleToPercent(yaw)}%`;
    document.getElementById('pb-pitch').style.width = `${poseAngleToPercent(pitch)}%`;

    // Color head pose bars based on threshold (±25° yaw, ±20° pitch)
    document.getElementById('pb-yaw').style.background = Math.abs(yaw) > 25 ? 'var(--warn)' : 'var(--ink)';
    document.getElementById('pb-pitch').style.background = Math.abs(pitch) > 20 ? 'var(--alert)' : 'var(--ink)';

    /* ── VIDEO ALERT OVERLAY ─────────── */
    const overlay = document.getElementById('video-alert-overlay');
    if (score >= 70) {
        overlay.classList.add('show');
        const reasons = detections.slice(0, 2).join(' · ') || 'High Risk Behavior';
        document.getElementById('overlay-reason').textContent = reasons;
        logAlert(`High risk detected — ${reasons}`, 'danger');
    } else {
        overlay.classList.remove('show');
    }

    /* ── SPECIFIC DETECTION ALERTS ─── */
    detections.forEach(det => {
        const dl = det.toLowerCase();
        if (dl.includes('talking') || dl.includes('mouth')) {
            logAlert('🗣 Talking detected', 'warn');
        }
        if (dl.includes('proximity')) {
            logAlert('👥 Proximity alert — students too close', 'warn');
        }
        if (dl.includes('looking down')) {
            logAlert('👇 Student looking down (possible hidden material)', 'warn');
        }
    });
}

/* ── FPS MOCK (backend doesn't return fps yet) ─────────── */
let lastPoll = Date.now();
function tickFPS() {
    const now = Date.now();
    const fps = Math.round(1000 / (now - lastPoll));
    lastPoll = now;
    const clamped = Math.min(fps, 30);
    document.getElementById('fps-display').textContent = `FPS: ${clamped}`;
    // update HUD
    const hud = document.getElementById('hud-bl');
    if (hud) hud.textContent = `YOLOv8 + MediaPipe · ${clamped} FPS`;
}

/* ── START ──────────────────────────────────────────────── */
setInterval(() => { pollStatus(); tickFPS(); }, 1000);
pollStatus(); // immediate first poll
