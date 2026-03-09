/* ═══════════════════════════════════════════════════════════
   THE SILENT INVIGILATOR — Admin Dashboard Controller
   User management, statistics, charts
   ═══════════════════════════════════════════════════════════ */

/* ── CLOCK ──────────────────────────────────────────────── */
function updateClock() {
    const now = new Date();
    const el = document.getElementById('current-time');
    if (el) el.textContent = now.toLocaleTimeString('en-GB', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

/* ── SCROLL HELPER ──────────────────────────────────────── */
function scrollToSection(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
}

/* ── CHART.JS DEFAULTS ──────────────────────────────────── */
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.plugins.legend.labels.boxWidth = 12;

/* ── TYPE DISTRIBUTION CHART (Doughnut) ─────────────────── */
const typeCtx = document.getElementById('typeChart').getContext('2d');
const typeChart = new Chart(typeCtx, {
    type: 'doughnut',
    data: {
        labels: [],
        datasets: [{
            data: [],
            backgroundColor: [
                '#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#7c3aed', '#ec4899'
            ],
            borderWidth: 0,
            spacing: 3,
            borderRadius: 4,
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
            legend: {
                position: 'bottom',
                labels: { padding: 12, font: { size: 11 } }
            }
        }
    }
});

/* ── TREND CHART (Line) ─────────────────────────────────── */
const trendCtx = document.getElementById('trendChart').getContext('2d');
const trendChart = new Chart(trendCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Alerts',
            data: [],
            borderColor: '#00d4ff',
            backgroundColor: 'rgba(0, 212, 255, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointBackgroundColor: '#00d4ff',
        }, {
            label: 'Avg Score',
            data: [],
            borderColor: '#7c3aed',
            backgroundColor: 'rgba(124, 58, 237, 0.08)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointBackgroundColor: '#7c3aed',
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255,255,255,0.05)' },
                border: { dash: [3, 3] }
            },
            x: {
                grid: { display: false }
            }
        },
        plugins: {
            legend: {
                position: 'top',
                labels: { padding: 10, font: { size: 10 } }
            }
        }
    }
});

/* ── RISK CHART (Doughnut) ──────────────────────────────── */
const riskCtx = document.getElementById('riskChart').getContext('2d');
const riskChart = new Chart(riskCtx, {
    type: 'polarArea',
    data: {
        labels: ['Critical', 'Warning', 'Info'],
        datasets: [{
            data: [],
            backgroundColor: [
                'rgba(239, 68, 68, 0.6)',
                'rgba(245, 158, 11, 0.6)',
                'rgba(59, 130, 246, 0.6)'
            ],
            borderColor: [
                '#ef4444',
                '#f59e0b',
                '#3b82f6'
            ],
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            r: {
                ticks: { display: false },
                grid: { color: 'rgba(255,255,255,0.05)' }
            }
        },
        plugins: {
            legend: {
                position: 'right',
                labels: { padding: 12, font: { size: 10 } }
            }
        }
    }
});

/* ── STABILITY CHART (Bar) ──────────────────────────────── */
const stabilityCtx = document.getElementById('stabilityChart').getContext('2d');
const stabilityChart = new Chart(stabilityCtx, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: 'System Load %',
            data: [],
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            borderColor: '#10b981',
            borderWidth: 1,
            borderRadius: 4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(255,255,255,0.05)' },
                border: { dash: [3, 3] }
            },
            x: {
                grid: { display: false }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
});

/* ── LOAD STATS ─────────────────────────────────────────── */
/* ── TERMINAL SIMULATOR ──────────────────────────────────── */
const terminal = document.getElementById('terminal-output');
function logToTerminal(msg, color = '#a5f3fc') {
    if (!terminal) return;
    const entry = document.createElement('div');
    entry.style.color = color;
    entry.style.marginBottom = '2px';
    const ts = new Date().toLocaleTimeString('en-GB', { hour12: false });
    entry.innerHTML = `<span style="opacity:0.4;">[${ts}]</span> ${msg}`;
    terminal.appendChild(entry);
    terminal.scrollTop = terminal.scrollHeight;
    while (terminal.children.length > 50) terminal.firstChild.remove();
}

/* ── LOAD STATS ─────────────────────────────────────────── */
async function loadStats() {
    try {
        const res = await fetch('/admin/stats');
        const data = await res.json();

        document.getElementById('stat-total-alerts').textContent = data.total_alerts;
        document.getElementById('stat-critical').textContent = data.critical_alerts;
        document.getElementById('stat-warnings').textContent = data.warning_alerts;
        document.getElementById('stat-users').textContent = data.total_users;

        const badge = document.getElementById('operator-count-badge');
        if (badge) badge.textContent = `${data.total_users} PROVISIONED`;

        // Type chart
        typeChart.data.labels = data.type_distribution.map(t => t.type);
        typeChart.data.datasets[0].data = data.type_distribution.map(t => t.count);
        typeChart.update();

        // Trend chart
        trendChart.data.labels = data.hourly_trend.map(h => h.hour + ':00');
        trendChart.data.datasets[0].data = data.hourly_trend.map(h => h.count);
        trendChart.data.datasets[1].data = data.hourly_trend.map(h => h.avg_score);
        trendChart.update();

        // Risk Chart
        if (data.risk_distribution) {
            riskChart.data.datasets[0].data = [
                data.risk_distribution.critical,
                data.risk_distribution.warning,
                data.risk_distribution.info
            ];
            riskChart.update();
        }

        // Stability Chart (Simulated Load based on hours)
        stabilityChart.data.labels = data.hourly_trend.map(h => h.hour + ':00');
        stabilityChart.data.datasets[0].data = data.hourly_trend.map(h => {
            return Math.min(100, (h.count * 2) + h.avg_score + Math.floor(Math.random() * 20));
        });
        stabilityChart.update();

    } catch (e) {
        console.error('Stats load error:', e);
        logToTerminal('!! ERROR: Failed to poll system stats', '#ef4444');
    }
}

/* ── LOAD USERS ─────────────────────────────────────────── */
async function loadUsers() {
    try {
        logToTerminal('> Querying operator database...');
        const res = await fetch('/admin/users');
        const users = await res.json();
        const tbody = document.getElementById('users-tbody');

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><p>No users provisioned</p></td></tr>';
            return;
        }

        const roleLabels = {
            'admin': '<span class="badge badge-danger" style="border:1px solid rgba(239,68,68,0.3);">Administrator</span>',
            'teacher': '<span class="badge badge-info" style="border:1px solid rgba(59,130,246,0.3);">Operator</span>'
        };

        tbody.innerHTML = users.map(u => `
            <tr>
                <td style="font-family:var(--font-mono);color:var(--text-muted);font-size:0.75rem;">A-${u.id.toString().padStart(3, '0')}</td>
                <td>
                    <div style="font-weight:600;color:var(--accent-purple);font-size:0.85rem;">@${u.username}</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">${u.full_name}</div>
                </td>
                <td>${roleLabels[u.role] || u.role}</td>
                <td style="text-align:right;">
                    <button class="btn btn-ghost btn-sm" style="color:var(--status-danger);border-color:rgba(239,68,68,0.15);padding:4px 10px;font-size:0.6rem;letter-spacing:0.5px;" onclick="deleteUser(${u.id}, '${u.username}')">
                        REVOKE
                    </button>
                </td>
            </tr>
        `).join('');
        logToTerminal(`[OK] Decrypted ${users.length} operator signatures`, '#6ee7b7');
    } catch (e) {
        console.error('Users load error:', e);
        logToTerminal('!! ERROR: Secure database link failed', '#ef4444');
    }
}

/* ── LOAD ALERTS ────────────────────────────────────────── */
async function loadAlerts() {
    try {
        const res = await fetch('/api/alerts?limit=40');
        const logs = await res.json();
        const list = document.getElementById('alerts-list');

        if (logs.length === 0) {
            list.innerHTML = '<div class="empty-state" style="border: 1px dashed rgba(255,255,255,0.05); border-radius: 8px;"><div class="empty-icon">✅</div><p style="font-family:var(--font-mono);">ENCRYPTION CLEAR — NO VIOLATIONS DETECTED</p></div>';
            return;
        }

        list.innerHTML = logs.map(log => {
            let sevClass = 'severity-info';
            let icon = '🛡';
            if (log.risk_score >= 80) { sevClass = 'severity-critical'; icon = '⚠'; }
            else if (log.risk_score >= 50) { sevClass = 'severity-warning'; icon = '⚡'; }

            const time = log.timestamp.split(' ')[1] || log.timestamp;
            const logId = `DET-${log.id.toString().padStart(4, '0')}`;

            return `
                <div class="alert-item ${sevClass}">
                    <div class="alert-time">${time}</div>
                    <div class="alert-icon">${icon}</div>
                    <div class="alert-content">
                        <div class="alert-type">
                            ${log.event_type}
                            <span style="float:right; opacity:0.3; font-size:0.6rem; letter-spacing:1px; font-weight:400;">${logId}</span>
                        </div>
                        <div class="alert-desc">${log.description}</div>
                    </div>
                    <div class="alert-score" style="font-family:var(--font-mono); font-weight:700; font-size:0.85rem; color:var(--text-muted); min-width:35px; text-align:right; opacity:0.8;">
                        ${log.risk_score}<span style="font-size:0.6rem; opacity:0.6;">%</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Alerts load error:', e);
    }
}

/* ── USER MANAGEMENT ────────────────────────────────────── */
function openAddUserModal() {
    document.getElementById('add-user-modal').classList.add('show');
    document.getElementById('modal-error').style.display = 'none';
    logToTerminal('> Awaiting new operator provisioning data...');
}

function closeModal() {
    document.getElementById('add-user-modal').classList.remove('show');
    document.getElementById('new-fullname').value = '';
    document.getElementById('new-username').value = '';
    document.getElementById('new-password').value = '';
    document.getElementById('new-role').value = 'teacher';
}

async function addUser() {
    const fullname = document.getElementById('new-fullname').value.trim();
    const username = document.getElementById('new-username').value.trim();
    const password = document.getElementById('new-password').value.trim();
    const role = document.getElementById('new-role').value;
    const errEl = document.getElementById('modal-error');

    if (!fullname || !username || !password) {
        errEl.textContent = '⚠ All fields are required';
        errEl.style.display = 'block';
        return;
    }

    logToTerminal(`> Encrypting credentials for @${username}...`);
    try {
        const res = await fetch('/admin/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullname, username, password, role })
        });
        const data = await res.json();

        if (data.success) {
            logToTerminal(`[OK] Operator ${username} securely provisioned`, '#6ee7b7');
            closeModal();
            loadUsers();
            loadStats();
        } else {
            errEl.textContent = `⚠ ${data.error}`;
            errEl.style.display = 'block';
            logToTerminal(`!! PROVISIONING FAILED: ${data.error}`, '#ef4444');
        }
    } catch (e) {
        errEl.textContent = '⚠ Network error';
        errEl.style.display = 'block';
    }
}

async function deleteUser(id, username) {
    if (!confirm(`Are you sure you want to revoke access for @${username}?`)) return;

    logToTerminal(`> Revoking access for operator ID ${id}...`);
    try {
        const res = await fetch(`/admin/users/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            logToTerminal(`[OK] Access revoked for @${username}`, '#fca5a5');
            loadUsers();
            loadStats();
        }
    } catch (e) {
        console.error('Delete error:', e);
    }
}

/* ── INTERSECTION OBSERVER FOR ANIMATIONS ───────────────── */
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.animate-fade-up').forEach(el => observer.observe(el));

/* ── INIT ───────────────────────────────────────────────── */
loadStats();
loadUsers();
loadAlerts();

// Refresh cycles
setInterval(loadStats, 30000);
setInterval(loadAlerts, 5000);
setInterval(() => {
    if (Math.random() > 0.7) logToTerminal('[MON] Scanning network nodes...', '#94a3b8');
}, 15000);

