/**
 * Distributed Time Sync — Dashboard Client-Side Logic
 * SocketIO real-time updates, Chart.js rendering, Space-Time diagram
 */

// ═══════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════

const NODE_COLORS = {
    '0': '#8b5cf6', // Server - Purple
    '1': '#10b981', // Node 1 - Emerald
    '2': '#f59e0b', // Node 2 - Amber
    '3': '#ec4899', // Node 3 - Pink
    '4': '#06b6d4', // Node 4 - Cyan
};

const NODE_COLORS_ALPHA = {
    '0': 'rgba(139, 92, 246, 0.2)',
    '1': 'rgba(16, 185, 129, 0.2)',
    '2': 'rgba(245, 158, 11, 0.2)',
    '3': 'rgba(236, 72, 153, 0.2)',
    '4': 'rgba(6, 182, 212, 0.2)',
};

// ═══════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════

let ntpData = {};
let logicEvents = [];
let offsetChart = null;
let delayChart = null;

// ═══════════════════════════════════════════════
// SocketIO Connection
// ═══════════════════════════════════════════════

const socket = io();

socket.on('connect', () => {
    console.log('[Dashboard] Connected to server');
    document.getElementById('statusBadge').querySelector('.status-text').textContent = 'Online';
    // Initial data fetch
    fetchInitialData();
});

socket.on('disconnect', () => {
    console.log('[Dashboard] Disconnected');
    document.getElementById('statusBadge').querySelector('.status-text').textContent = 'Offline';
    document.querySelector('.status-dot').style.background = '#ef4444';
});

socket.on('ntp_update', (data) => {
    console.log('[Dashboard] NTP update:', data);
    ntpData[data.node_id] = data.data;
    updateNTPUI();
});

socket.on('logic_update', (data) => {
    console.log('[Dashboard] Logic update:', data);
    logicEvents.push(data);
    updateLogicUI();
});

// ═══════════════════════════════════════════════
// Data Fetching
// ═══════════════════════════════════════════════

async function fetchInitialData() {
    try {
        const [ntpRes, logicRes] = await Promise.all([
            fetch('/api/ntp/results'),
            fetch('/api/logic/events')
        ]);
        ntpData = await ntpRes.json();
        logicEvents = await logicRes.json();
        updateNTPUI();
        updateLogicUI();
    } catch (e) {
        console.error('[Dashboard] Fetch error:', e);
    }
}

// ═══════════════════════════════════════════════
// Tab Navigation
// ═══════════════════════════════════════════════

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active from all
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        // Set active
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        const sectionMap = { ntp: 'ntpSection', logic: 'logicSection', compare: 'compareSection' };
        document.getElementById(sectionMap[tab]).classList.add('active');

        // Redraw charts on tab switch
        if (tab === 'logic') {
            setTimeout(() => drawTimeline(), 100);
        }
    });
});

// ═══════════════════════════════════════════════
// Server Time Clock
// ═══════════════════════════════════════════════

function updateServerTime() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    const ms = String(now.getMilliseconds()).padStart(3, '0');
    document.getElementById('serverTime').textContent = `${h}:${m}:${s}.${ms}`;
}
setInterval(updateServerTime, 50);
updateServerTime();

// ═══════════════════════════════════════════════
// NTP UI Updates
// ═══════════════════════════════════════════════

function updateNTPUI() {
    const entries = Object.entries(ntpData);
    const count = entries.length;

    // Update badge
    document.getElementById('ntpBadge').textContent = count;
    document.getElementById('syncedNodes').textContent = count;

    if (count === 0) return;

    // Calculate averages
    let totalDelay = 0, totalOffset = 0, totalError = 0;
    entries.forEach(([_, d]) => {
        totalDelay += Math.abs(d.delay || 0);
        totalOffset += Math.abs(d.offset || 0);
        totalError += (d.remaining_error_ms || 0);
    });

    document.getElementById('avgDelay').textContent = `${(totalDelay / count * 1000).toFixed(1)}ms`;
    document.getElementById('avgOffset').textContent = `${(totalOffset / count).toFixed(3)}s`;
    document.getElementById('avgAccuracy').textContent = `${(totalError / count).toFixed(1)}ms`;

    // Update table
    updateNTPTable(entries);

    // Update charts
    updateNTPCharts(entries);
}

function updateNTPTable(entries) {
    const tbody = document.getElementById('ntpTableBody');
    tbody.innerHTML = '';

    entries.sort((a, b) => parseInt(a[0]) - parseInt(b[0]));

    entries.forEach(([nodeId, d]) => {
        const tr = document.createElement('tr');
        tr.className = 'new-row';

        const formatTs = (key) => d[key] || '—';
        const formatT = (v) => {
            if (!v || typeof v === 'string') return v || '—';
            const date = new Date(v * 1000);
            return date.toLocaleTimeString('vi-VN', { hour12: false }) + '.' +
                   String(date.getMilliseconds()).padStart(3, '0');
        };

        tr.innerHTML = `
            <td><span class="node-badge node-${nodeId}">Node ${nodeId}</span></td>
            <td style="color: ${Math.abs(d.fake_offset) > 0 ? '#ef4444' : '#94a3b8'}">${(d.fake_offset || 0).toFixed(3)}s</td>
            <td>${formatT(d.T1)}</td>
            <td>${formatT(d.T2)}</td>
            <td>${formatT(d.T3)}</td>
            <td>${formatT(d.T4)}</td>
            <td>${((d.delay || 0) * 1000).toFixed(3)}ms</td>
            <td style="color: #f59e0b">${(d.offset || 0).toFixed(6)}s</td>
            <td style="color: #10b981">${(d.remaining_error_ms || 0).toFixed(3)}ms</td>
            <td><span class="sync-status synced">✓ Synced</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function updateNTPCharts(entries) {
    const labels = entries.map(([id, _]) => `Node ${id}`);
    const fakeOffsets = entries.map(([_, d]) => d.fake_offset || 0);
    const calcOffsets = entries.map(([_, d]) => d.offset || 0);
    const delays = entries.map(([_, d]) => (d.delay || 0) * 1000);
    const bgColors = entries.map(([id, _]) => NODE_COLORS[id] || '#94a3b8');
    const bgAlpha = entries.map(([id, _]) => NODE_COLORS_ALPHA[id] || 'rgba(148,163,184,0.2)');

    // Offset chart
    const ctxOffset = document.getElementById('ntpOffsetChart').getContext('2d');
    if (offsetChart) offsetChart.destroy();
    offsetChart = new Chart(ctxOffset, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Fake Offset (s)',
                    data: fakeOffsets,
                    backgroundColor: 'rgba(239, 68, 68, 0.3)',
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    borderRadius: 6,
                },
                {
                    label: 'NTP Calculated Offset (s)',
                    data: calcOffsets,
                    backgroundColor: 'rgba(16, 185, 129, 0.3)',
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderRadius: 6,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: "'Inter'" } }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#64748b' },
                    grid: { color: 'rgba(255,255,255,0.03)' }
                },
                y: {
                    ticks: { color: '#64748b', callback: v => v.toFixed(1) + 's' },
                    grid: { color: 'rgba(255,255,255,0.03)' }
                }
            }
        }
    });

    // Delay chart
    const ctxDelay = document.getElementById('ntpDelayChart').getContext('2d');
    if (delayChart) delayChart.destroy();
    delayChart = new Chart(ctxDelay, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Network Delay (ms)',
                data: delays,
                backgroundColor: bgAlpha,
                borderColor: bgColors,
                borderWidth: 2,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: "'Inter'" } }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#64748b' },
                    grid: { color: 'rgba(255,255,255,0.03)' }
                },
                y: {
                    ticks: { color: '#64748b', callback: v => v.toFixed(1) + 'ms' },
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    beginAtZero: true,
                }
            }
        }
    });
}

// ═══════════════════════════════════════════════
// Logical Clock UI Updates
// ═══════════════════════════════════════════════

function updateLogicUI() {
    document.getElementById('logicBadge').textContent = logicEvents.length;

    if (logicEvents.length === 0) return;

    updateLogicTable();
    drawTimeline();
    detectConcurrentEvents();
}

function updateLogicTable() {
    const tbody = document.getElementById('logicTableBody');
    tbody.innerHTML = '';

    logicEvents.forEach((evt, i) => {
        const tr = document.createElement('tr');
        tr.className = 'new-row';

        const nodeId = evt.node_id !== undefined ? evt.node_id : '?';
        const evtType = evt.type || '?';

        let detail = '';
        if (evtType === 'send') {
            detail = `→ Node ${evt.target_node}: "${evt.message || ''}"`;
        } else if (evtType === 'receive') {
            detail = `← Node ${evt.from_node}`;
        } else {
            detail = 'Sự kiện nội bộ';
        }

        const vc = evt.vector_clock ? JSON.stringify(evt.vector_clock) : '—';

        tr.innerHTML = `
            <td style="color: #64748b">${i + 1}</td>
            <td>${evt.time_str || evt.received_at_str || '—'}</td>
            <td><span class="node-badge node-${nodeId}">Node ${nodeId}</span></td>
            <td><span class="event-badge ${evtType}">${evtType.toUpperCase()}</span></td>
            <td style="font-family: var(--font-sans); font-size: 12px;">${detail}</td>
            <td style="color: #f59e0b; font-weight: 600;">${evt.lamport_clock || 0}</td>
            <td style="color: #06b6d4;">${vc}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ═══════════════════════════════════════════════
// Space-Time Diagram (Canvas)
// ═══════════════════════════════════════════════

function drawTimeline() {
    const canvas = document.getElementById('timelineDiagram');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;

    // Set canvas size
    const dpr = window.devicePixelRatio || 1;
    const width = container.clientWidth;
    const minHeight = 400;
    const eventHeight = 50;
    const height = Math.max(minHeight, logicEvents.length * eventHeight + 120);

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, width, height);

    if (logicEvents.length === 0) {
        ctx.fillStyle = '#64748b';
        ctx.font = '14px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('Chưa có sự kiện. Chờ các Client tạo sự kiện...', width / 2, height / 2);
        return;
    }

    // Layout: node columns
    const nodes = new Set();
    logicEvents.forEach(evt => {
        if (evt.node_id !== undefined) nodes.add(evt.node_id);
        if (evt.target_node !== undefined) nodes.add(evt.target_node);
        if (evt.from_node !== undefined) nodes.add(evt.from_node);
    });
    const sortedNodes = Array.from(nodes).sort((a, b) => a - b);
    const numNodes = Math.max(sortedNodes.length, 1);

    const marginLeft = 80;
    const marginRight = 40;
    const marginTop = 60;
    const marginBottom = 40;
    const usableWidth = width - marginLeft - marginRight;

    const nodeX = {};
    sortedNodes.forEach((nid, i) => {
        nodeX[nid] = marginLeft + (usableWidth / (numNodes + 1)) * (i + 1);
    });

    // Draw node timeline lines (vertical)
    sortedNodes.forEach(nid => {
        const x = nodeX[nid];
        const color = NODE_COLORS[String(nid)] || '#94a3b8';

        // Vertical line
        ctx.beginPath();
        ctx.strokeStyle = color + '40';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.moveTo(x, marginTop);
        ctx.lineTo(x, height - marginBottom);
        ctx.stroke();
        ctx.setLineDash([]);

        // Node label
        ctx.fillStyle = color;
        ctx.font = 'bold 14px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(`Node ${nid}`, x, marginTop - 15);

        // Circle at top
        ctx.beginPath();
        ctx.arc(x, marginTop, 6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
    });

    // Draw events
    const yStep = Math.min(eventHeight, (height - marginTop - marginBottom) / (logicEvents.length + 1));

    // Track y-positions for arrows
    const eventPositions = [];

    logicEvents.forEach((evt, i) => {
        const y = marginTop + (i + 1) * yStep;
        const nodeId = evt.node_id;
        const x = nodeX[nodeId];
        if (x === undefined) return;

        const color = NODE_COLORS[String(nodeId)] || '#94a3b8';

        eventPositions.push({ x, y, nodeId, evt, index: i });

        // Draw event dot
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Inner dot
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#0a0e17';
        ctx.fill();

        // Label (Lamport clock value)
        ctx.fillStyle = '#f1f5f9';
        ctx.font = 'bold 11px JetBrains Mono';
        ctx.textAlign = 'left';
        ctx.fillText(`L=${evt.lamport_clock || 0}`, x + 14, y + 4);

        // Event type on left
        ctx.fillStyle = '#64748b';
        ctx.font = '10px Inter';
        ctx.textAlign = 'right';
        const typeLabel = (evt.type || '').toUpperCase();
        ctx.fillText(typeLabel, x - 14, y + 4);
    });

    // Draw message arrows (send → receive pairs)
    for (let i = 0; i < logicEvents.length; i++) {
        const evt = logicEvents[i];
        if (evt.type !== 'send') continue;

        // Find matching receive event
        for (let j = i + 1; j < logicEvents.length; j++) {
            const recv = logicEvents[j];
            if (recv.type === 'receive' && recv.from_node === evt.node_id && recv.node_id === evt.target_node) {
                const sendPos = eventPositions.find(p => p.index === i);
                const recvPos = eventPositions.find(p => p.index === j);

                if (sendPos && recvPos) {
                    const color = NODE_COLORS[String(evt.node_id)] || '#94a3b8';

                    // Draw arrow
                    ctx.beginPath();
                    ctx.strokeStyle = color + 'aa';
                    ctx.lineWidth = 2;
                    ctx.moveTo(sendPos.x, sendPos.y);
                    ctx.lineTo(recvPos.x, recvPos.y);
                    ctx.stroke();

                    // Arrowhead
                    const angle = Math.atan2(recvPos.y - sendPos.y, recvPos.x - sendPos.x);
                    const headLen = 10;
                    ctx.beginPath();
                    ctx.fillStyle = color + 'aa';
                    ctx.moveTo(recvPos.x, recvPos.y);
                    ctx.lineTo(recvPos.x - headLen * Math.cos(angle - 0.3), recvPos.y - headLen * Math.sin(angle - 0.3));
                    ctx.lineTo(recvPos.x - headLen * Math.cos(angle + 0.3), recvPos.y - headLen * Math.sin(angle + 0.3));
                    ctx.closePath();
                    ctx.fill();

                    // Message label
                    const midX = (sendPos.x + recvPos.x) / 2;
                    const midY = (sendPos.y + recvPos.y) / 2;
                    if (evt.message) {
                        ctx.fillStyle = '#94a3b8';
                        ctx.font = 'italic 10px Inter';
                        ctx.textAlign = 'center';
                        const truncMsg = evt.message.length > 15 ? evt.message.substring(0, 15) + '...' : evt.message;
                        ctx.fillText(`"${truncMsg}"`, midX, midY - 8);
                    }
                }
                break;
            }
        }
    }

    // Y-axis label
    ctx.fillStyle = '#64748b';
    ctx.font = '12px Inter';
    ctx.textAlign = 'center';
    ctx.save();
    ctx.translate(20, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Time →', 0, 0);
    ctx.restore();
}

// ═══════════════════════════════════════════════
// Concurrent Events Detection
// ═══════════════════════════════════════════════

function detectConcurrentEvents() {
    const card = document.getElementById('concurrentCard');
    const list = document.getElementById('concurrentList');

    // Find events with same Lamport value but different Vector clocks
    // that are NOT causally related
    const concurrent = [];

    for (let i = 0; i < logicEvents.length; i++) {
        for (let j = i + 1; j < logicEvents.length; j++) {
            const a = logicEvents[i];
            const b = logicEvents[j];

            if (!a.vector_clock || !b.vector_clock) continue;
            if (a.node_id === b.node_id) continue;

            // Check if concurrent: neither a <= b nor b <= a
            const aLeqB = a.vector_clock.every((v, k) => v <= b.vector_clock[k]);
            const bLeqA = b.vector_clock.every((v, k) => v <= a.vector_clock[k]);

            if (!aLeqB && !bLeqA) {
                // These are concurrent events!
                const sameLamport = a.lamport_clock === b.lamport_clock;
                concurrent.push({
                    event_a: { index: i + 1, ...a },
                    event_b: { index: j + 1, ...b },
                    same_lamport: sameLamport,
                });
            }
        }
    }

    if (concurrent.length === 0) {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';
    list.innerHTML = '';

    concurrent.forEach(c => {
        const div = document.createElement('div');
        div.className = 'concurrent-item';
        div.innerHTML = `
            <div class="label">⚡ Concurrent Events Detected</div>
            <div>Event #${c.event_a.index} (Node ${c.event_a.node_id}, L=${c.event_a.lamport_clock}, V=${JSON.stringify(c.event_a.vector_clock)})
                <strong> || </strong>
                Event #${c.event_b.index} (Node ${c.event_b.node_id}, L=${c.event_b.lamport_clock}, V=${JSON.stringify(c.event_b.vector_clock)})
            </div>
            <div style="margin-top: 4px; color: ${c.same_lamport ? '#ef4444' : '#94a3b8'}; font-size: 12px;">
                ${c.same_lamport
                    ? '⚠ Lamport Clock CÙNG GIÁ TRỊ — không phân biệt được! Vector Clock phát hiện concurrent.'
                    : 'Lamport Clock khác giá trị nhưng KHÔNG thể kết luận thứ tự. Vector Clock phát hiện concurrent.'}
            </div>
        `;
        list.appendChild(div);
    });
}

// ═══════════════════════════════════════════════
// Auto-refresh polling (backup for SocketIO)
// ═══════════════════════════════════════════════

setInterval(() => {
    fetchInitialData();
}, 5000);

// Handle window resize for timeline
window.addEventListener('resize', () => {
    if (document.getElementById('logicSection').classList.contains('active')) {
        drawTimeline();
    }
});

console.log('[Dashboard] Initialized');
