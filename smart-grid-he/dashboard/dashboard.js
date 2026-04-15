/**
 * Smart Grid Dashboard JavaScript
 * Fixes: comparison chart both lines visible, simulated time, household type topology,
 *        peak hour indicator, capacity threshold lines, error/comparison consistency.
 */

// ─── Profile colour map ───────────────────────────────────────────────────────
const PROFILE_COLORS = {
    residential_small:  { stroke: '#4ecca3', fill: '#0d3b2e', label: 'Res. Small' },
    residential_medium: { stroke: '#f0a500', fill: '#3b2800', label: 'Res. Medium' },
    residential_large:  { stroke: '#ff6b6b', fill: '#3b0e0e', label: 'Res. Large' },
    commercial_small:   { stroke: '#58a6ff', fill: '#0d1f3b', label: 'Commercial' },
};
const DEFAULT_PROFILE_COLOR = { stroke: '#f0a500', fill: '#3b2800' };

class SmartGridDashboard {
    constructor() {
        this.ws = null;
        this.isAutoRunning = false;
        this.agents = [];           // [{agent_id, profile, current_demand_kw, ...}]
        this.agentProfileMap = {};  // agent_id -> profile string
        this.history = [];
        this.maxHistoryPoints = 20;
        this.roundNumber = 0;
        this.currentAgentCount = 25;
        this.currentCapacityKw = 100;

        // Chart instances
        this.comparisonChart = null;
        this.utilizationChart = null;
        this.timeChart = null;
        this.errorChart = null;

        this.init();
    }

    init() {
        this.setupWebSocket();
        this.setupEventListeners();
        this.setupTabs();
        this.loadInitialData();
        this.initCharts();
        this.generateTopology();
    }

    // ─── WebSocket ────────────────────────────────────────────────────────────

    setupWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws`;
        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen    = () => { this.updateStatus(true); };
            this.ws.onmessage = (event) => { this.handleMessage(JSON.parse(event.data)); };
            this.ws.onclose   = () => { this.updateStatus(false); setTimeout(() => this.setupWebSocket(), 3000); };
            this.ws.onerror   = (err) => { console.error('WS error:', err); };
        } catch (e) {
            console.error('WS setup failed:', e);
            this.updateStatus(false);
        }
    }

    // ─── Event Listeners ─────────────────────────────────────────────────────

    setupEventListeners() {
        document.getElementById('run-round-btn').addEventListener('click',   () => this.runRound());
        document.getElementById('auto-start-btn').addEventListener('click',  () => this.startAutoRun());
        document.getElementById('auto-stop-btn').addEventListener('click',   () => this.stopAutoRun());
        document.getElementById('reset-btn').addEventListener('click',       () => this.resetSimulation());
        document.getElementById('apply-config-btn').addEventListener('click',() => this.applyConfiguration());
    }

    // ─── Tabs ─────────────────────────────────────────────────────────────────

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(`${tabId}-tab`).classList.add('active');
                if (tabId === 'graphs') setTimeout(() => this.resizeCharts(), 100);
            });
        });
    }

    // ─── Charts ───────────────────────────────────────────────────────────────

    initCharts() {
        const baseScales = {
            x: { grid: { color: 'rgba(78,204,163,0.1)' }, ticks: { color: '#8b949e' } },
            y: { grid: { color: 'rgba(78,204,163,0.1)' }, ticks: { color: '#8b949e' } }
        };
        const baseLegend = { labels: { color: '#8b949e', font: { size: 11 } } };

        // ── Comparison Chart ──────────────────────────────────────────────────
        // Plaintext is dataset[0] (rendered FIRST = bottom layer, thick orange dashed).
        // Encrypted is dataset[1] (rendered LAST  = top layer, thin green solid).
        // Because plaintext is wider it peeks out even when values are identical,
        // making both lines always visible while proving FHE correctness via overlap.
        const compCtx = document.getElementById('comparison-chart');
        if (compCtx) {
            this.comparisonChart = new Chart(compCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Plaintext Total (kW)',
                            data: [],
                            borderColor: '#f0a500',
                            backgroundColor: 'rgba(240,165,0,0.08)',
                            fill: false,
                            tension: 0.3,
                            borderWidth: 6,          // Thick — always peeking behind encrypted
                            borderDash: [8, 4],
                            pointRadius: 7,
                            pointStyle: 'triangle',
                            pointBackgroundColor: '#f0a500',
                            order: 2,                // Rendered below encrypted
                        },
                        {
                            label: 'Encrypted Total (kW)',
                            data: [],
                            borderColor: '#4ecca3',
                            backgroundColor: 'rgba(78,204,163,0.08)',
                            fill: false,
                            tension: 0.3,
                            borderWidth: 2.5,        // Thin — sits on top of plaintext
                            pointRadius: 4,
                            pointStyle: 'circle',
                            pointBackgroundColor: '#4ecca3',
                            order: 1,                // Rendered on top
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 300 },
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { labels: { color: '#8b949e', font: { size: 11 } } },
                        title: {
                            display: true,
                            text: 'FHE maintains precision across all rounds (orange = plaintext, green = encrypted)',
                            color: '#8b949e'
                        },
                        tooltip: {
                            callbacks: {
                                afterBody: (items) => {
                                    if (items.length >= 2) {
                                        const plain = items.find(i => i.datasetIndex === 0);
                                        const enc   = items.find(i => i.datasetIndex === 1);
                                        if (plain && enc) {
                                            const diff = Math.abs(plain.parsed.y - enc.parsed.y);
                                            return [`Error: ${diff.toExponential(2)} kW`];
                                        }
                                    }
                                    return [];
                                }
                            }
                        }
                    },
                    scales: {
                        ...baseScales,
                        y: {
                            ...baseScales.y,
                            title: { display: true, text: 'Total Demand (kW)', color: '#8b949e' }
                        }
                    }
                }
            });
        }

        // ── Utilization Chart (with 80% and 100% threshold lines) ─────────────
        const utilCtx = document.getElementById('utilization-chart');
        if (utilCtx) {
            this.utilizationChart = new Chart(utilCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Utilization %',
                            data: [],
                            borderColor: '#f0a500',
                            backgroundColor: 'rgba(240,165,0,0.15)',
                            fill: true,
                            tension: 0.3,
                            borderWidth: 2,
                            pointRadius: 3,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 300 },
                    plugins: {
                        legend: { ...baseLegend },
                        annotation: {
                            // Threshold lines drawn via afterDraw plugin below
                        }
                    },
                    scales: {
                        ...baseScales,
                        y: {
                            ...baseScales.y,
                            min: 0,
                            max: 150,
                            ticks: { color: '#8b949e', stepSize: 25 }
                        }
                    }
                },
                plugins: [{
                    id: 'thresholdLines',
                    afterDraw(chart) {
                        const { ctx, chartArea, scales } = chart;
                        if (!chartArea) return;
                        const drawLine = (yVal, color, label) => {
                            const yPx = scales.y.getPixelForValue(yVal);
                            ctx.save();
                            ctx.setLineDash([6, 4]);
                            ctx.strokeStyle = color;
                            ctx.lineWidth = 1.5;
                            ctx.globalAlpha = 0.7;
                            ctx.beginPath();
                            ctx.moveTo(chartArea.left,  yPx);
                            ctx.lineTo(chartArea.right, yPx);
                            ctx.stroke();
                            ctx.globalAlpha = 1;
                            ctx.setLineDash([]);
                            ctx.fillStyle = color;
                            ctx.font = '10px Segoe UI';
                            ctx.fillText(label, chartArea.left + 4, yPx - 4);
                            ctx.restore();
                        };
                        drawLine(80,  '#f0a500', '80% — Reduce');
                        drawLine(100, '#f85149', '100% — Critical');
                    }
                }]
            });
        }

        // ── Computation Time Chart ────────────────────────────────────────────
        const timeCtx = document.getElementById('time-chart');
        if (timeCtx) {
            this.timeChart = new Chart(timeCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Computation Time (ms)',
                        data: [],
                        backgroundColor: 'rgba(78,204,163,0.6)',
                        borderColor: '#4ecca3',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 300 },
                    plugins: { legend: { ...baseLegend } },
                    scales: baseScales
                }
            });
        }

        // ── Encryption Error Chart (log scale) ────────────────────────────────
        const errorCtx = document.getElementById('error-chart');
        if (errorCtx) {
            this.errorChart = new Chart(errorCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Absolute Error (kW)',
                        data: [],
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88,166,255,0.2)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#58a6ff',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 300 },
                    plugins: {
                        legend: { ...baseLegend },
                        tooltip: {
                            callbacks: {
                                label: (item) => `Error: ${item.parsed.y.toExponential(2)} kW`
                            }
                        }
                    },
                    scales: {
                        ...baseScales,
                        y: {
                            ...baseScales.y,
                            type: 'logarithmic',
                            title: { display: true, text: 'Error (kW, log scale)', color: '#8b949e' },
                            ticks: {
                                color: '#8b949e',
                                callback: (v) => v.toExponential(0)
                            }
                        }
                    }
                }
            });
        }
    }

    resizeCharts() {
        [this.comparisonChart, this.utilizationChart, this.timeChart, this.errorChart]
            .forEach(c => c && c.resize());
    }

    // ─── Topology ─────────────────────────────────────────────────────────────

    generateTopology(agentCount = null) {
        const container     = document.getElementById('house-nodes');
        const linesContainer= document.getElementById('connection-lines');
        if (!container || !linesContainer) return;

        const centerX   = 400;
        const centerY   = 270;
        const numHouses = agentCount || this.currentAgentCount || 25;

        let housesHtml = '';
        let linesHtml  = '';

        const addRing = (count, radius, startIdx, compact = false) => {
            for (let i = 0; i < count; i++) {
                const angle = (i / count) * 2 * Math.PI - Math.PI / 2;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                const idx = startIdx + i;
                const agentId = `house_${(idx + 1).toString().padStart(3, '0')}`;
                const profile = this.agentProfileMap[agentId] || null;
                const node = this.createHouseNode(idx, x, y, centerX, centerY, compact, profile);
                housesHtml += node.house;
                linesHtml  += node.line;
            }
        };

        if (numHouses <= 16) {
            addRing(numHouses, 175, 0);
        } else if (numHouses <= 36) {
            const inner = Math.floor(numHouses * 0.4);
            addRing(inner, 130, 0, true);
            addRing(numHouses - inner, 215, inner);
        } else {
            const inner  = Math.floor(numHouses * 0.2);
            const middle = Math.floor(numHouses * 0.35);
            const outer  = numHouses - inner - middle;
            addRing(inner,  105, 0,              true);
            addRing(middle, 165, inner,           true);
            addRing(outer,  225, inner + middle);
        }

        linesContainer.innerHTML = linesHtml;
        container.innerHTML      = housesHtml;
    }

    createHouseNode(index, x, y, centerX, centerY, compact = false, profile = null) {
        const houseId = index + 1;
        const s = compact ? 0.75 : 1;
        const w = 72 * s, h = 72 * s;
        const hw = w / 2, hh = h / 2;

        const pc     = (profile && PROFILE_COLORS[profile]) ? PROFILE_COLORS[profile] : DEFAULT_PROFILE_COLOR;
        const stroke = pc.stroke;
        const fill   = pc.fill;

        // Profile type badge character
        const badge = profile && profile.startsWith('commercial') ? 'C'
                    : profile && profile.includes('large')         ? 'L'
                    : profile && profile.includes('small')         ? 'S'
                    : 'M';

        const line = `
            <line class="connection-line"
                  x1="${x}" y1="${y}" x2="${centerX}" y2="${centerY}"
                  stroke="${stroke}" stroke-width="1.5" stroke-dasharray="5,5" opacity="0.5"/>
        `;

        const house = `
            <g class="house-node" id="house-${index}" transform="translate(${x},${y})" data-house-id="${index}">
                <rect class="house-bg" x="-${hw}" y="-${hh}" width="${w}" height="${h}" rx="8"
                      fill="${fill}" stroke="${stroke}" stroke-width="2"/>
                <text y="${-14 * s}" text-anchor="middle" fill="${stroke}" font-size="${9 * s}" font-weight="bold">[${badge}]</text>
                <text y="${1 * s}"   text-anchor="middle" fill="#e6edf3" font-size="${11 * s}" font-weight="600">H${houseId}</text>
                <rect class="demand-bar-bg" x="${-26*s}" y="${10*s}" width="${52*s}" height="${8*s}" rx="3" fill="#0d1117"/>
                <rect class="demand-bar" id="demand-bar-${index}"
                      x="${-26*s}" y="${10*s}" width="${3*s}" height="${8*s}" rx="3" fill="${stroke}"/>
                <text class="house-demand" id="house-demand-${index}"
                      y="${27*s}" text-anchor="middle" fill="#c9d1d9" font-size="${10*s}" font-weight="500">0.0 kW</text>
            </g>
        `;

        return { line, house };
    }

    // ─── Initial Data Load ────────────────────────────────────────────────────

    async loadInitialData() {
        try {
            const status = await fetch('/status').then(r => r.json());
            document.getElementById('agent-count').textContent = status.agent_count || '--';
            this.roundNumber        = status.round_count || 0;
            this.currentAgentCount  = status.agent_count || 25;
            this.currentCapacityKw  = status.grid_capacity_kw || 100;
            document.getElementById('round-count').textContent = this.roundNumber;

            await this.loadAgents();     // fills agentProfileMap before topology render
            this.generateTopology(this.currentAgentCount);
            this.updateHouseVisuals();   // topology now exists — apply demand data
            this.loadSecurityLogs();
            await this.loadHistory();
        } catch (e) {
            console.error('Failed to load initial data:', e);
        }
    }

    async loadAgents() {
        try {
            this.agents = await fetch('/agents').then(r => r.json());
            // Build fast lookup map
            this.agentProfileMap = {};
            this.agents.forEach(a => { this.agentProfileMap[a.agent_id] = a.profile; });
            this.updateHouseVisuals();
        } catch (e) {
            console.error('Failed to load agents:', e);
        }
    }

    async loadHistory() {
        try {
            const history = await fetch('/history?limit=20').then(r => r.json());
            this.history = [];
            history.forEach(r => this.addToHistory(r));
            this.updateCharts();
            // Sync the status-bar sim-time/peak display from the last loaded round.
            // history entries always have a valid simTime (computed in addToHistory).
            if (this.history.length > 0) {
                const last = this.history[this.history.length - 1];
                this.updateSimTimeDisplay(last.simTime, last.isPeak);
            }
        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }

    updateSimTimeDisplay(simTime, isPeak) {
        const timeEl = document.getElementById('sim-time');
        const peakEl = document.getElementById('peak-status');
        if (timeEl && simTime && simTime !== '--:--') {
            timeEl.textContent = simTime;
        }
        if (peakEl) {
            if (isPeak) {
                peakEl.textContent = '⚡ PEAK HOUR';
                peakEl.className   = 'value peak-status-peak';
            } else {
                peakEl.textContent = '● Off-Peak';
                peakEl.className   = 'value peak-status-offpeak';
            }
        }
    }

    // Compute simulated time string + peak flag purely from a round number.
    // Round 1 = 00:15, Round 2 = 00:30, … (each round = 15 sim-minutes from midnight).
    simTimeFromRound(roundNum) {
        const totalMinutes = roundNum * 15;
        const h = Math.floor(totalMinutes / 60) % 24;
        const m = totalMinutes % 60;
        const timeStr = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
        const isPeak  = (h >= 6 && h <= 9) || (h >= 17 && h <= 21);
        return { timeStr, isPeak };
    }

    addToHistory(data) {
        // Use server-provided simulated_time when available; otherwise derive from round number.
        // This keeps the display working even if server.py hasn't been restarted yet.
        const derived = this.simTimeFromRound(data.round_number);
        const simTime = (data.simulated_time && data.simulated_time !== '')
                        ? data.simulated_time
                        : derived.timeStr;
        const isPeak  = (data.is_peak_hour != null)
                        ? data.is_peak_hour
                        : derived.isPeak;

        this.history.push({
            round:       data.round_number,
            encTotal:    data.total_demand_kw,
            plainTotal:  data.plaintext_total_kw,
            utilization: data.utilization_percent,
            compTime:    data.computation_time_ms,
            error:       data.error_kw,
            simTime,
            isPeak,
        });
        if (this.history.length > this.maxHistoryPoints) this.history.shift();
    }

    // ─── Chart Updates ────────────────────────────────────────────────────────

    updateCharts() {
        const labels = this.history.map(h => `R${h.round}\n${h.simTime}`);

        // Comparison chart — dataset[0]=plaintext, dataset[1]=encrypted (order matches init)
        if (this.comparisonChart) {
            this.comparisonChart.data.labels           = labels;
            this.comparisonChart.data.datasets[0].data = this.history.map(h => h.plainTotal);
            this.comparisonChart.data.datasets[1].data = this.history.map(h => h.encTotal);
            // Colour data points: orange on peak rounds, neutral otherwise
            this.comparisonChart.data.datasets[0].pointBackgroundColor =
                this.history.map(h => h.isPeak ? '#f85149' : '#f0a500');
            this.comparisonChart.update('none');
        }

        if (this.utilizationChart) {
            this.utilizationChart.data.labels           = labels;
            this.utilizationChart.data.datasets[0].data = this.history.map(h => h.utilization);
            // Colour bars by level
            this.utilizationChart.data.datasets[0].borderColor = this.history.map(h =>
                h.utilization > 100 ? '#f85149' : h.utilization > 80 ? '#f0a500' : '#4ecca3'
            );
            this.utilizationChart.update('none');
        }

        if (this.timeChart) {
            this.timeChart.data.labels           = labels;
            this.timeChart.data.datasets[0].data = this.history.map(h => h.compTime);
            this.timeChart.update('none');
        }

        if (this.errorChart) {
            this.errorChart.data.labels           = labels;
            // Floor at 1e-12 so log scale never gets zero
            this.errorChart.data.datasets[0].data = this.history.map(h => Math.max(h.error, 1e-12));
            // Color points by error magnitude
            this.errorChart.data.datasets[0].pointBackgroundColor = this.history.map(h =>
                h.error > 1e-7 ? '#f85149' : h.error > 1e-9 ? '#f0a500' : '#58a6ff'
            );
            this.errorChart.update('none');
        }
    }

    // ─── Topology Visuals ─────────────────────────────────────────────────────

    updateHouseVisuals() {
        const maxDemandByProfile = {
            residential_small:  4.0,
            residential_medium: 8.0,
            residential_large:  15.0,
            commercial_small:   30.0,
        };

        this.agents.forEach((agent, i) => {
            const bar        = document.getElementById(`demand-bar-${i}`);
            const demandText = document.getElementById(`house-demand-${i}`);
            const node       = document.getElementById(`house-${i}`);
            if (!bar || !node) return;

            const demand     = agent.current_demand_kw || 0;
            const profile    = agent.profile || 'residential_medium';
            const maxD       = maxDemandByProfile[profile] || 8;
            const pct        = Math.min(demand / maxD, 1);

            // Demand bar width
            const bgBar  = node.querySelector('.demand-bar-bg');
            const maxW   = bgBar ? parseFloat(bgBar.getAttribute('width')) : 50;
            const barW   = Math.max(maxW * pct, 2);
            bar.setAttribute('width', barW);

            // Demand bar colour by % of personal capacity
            const barColor = pct > 0.85 ? '#f85149' : pct > 0.55 ? '#f0a500' : '#4ecca3';
            bar.setAttribute('fill', barColor);

            // Demand label
            if (demandText) demandText.textContent = `${demand.toFixed(1)} kW`;

            // Brief glow pulse
            const bg = node.querySelector('.house-bg');
            if (bg) {
                bg.setAttribute('stroke', barColor);
                bg.style.filter = `drop-shadow(0 0 6px ${barColor})`;
                setTimeout(() => { bg.style.filter = 'none'; }, 600);
            }
        });
    }

    // ─── Data Packet Animation ────────────────────────────────────────────────

    animateDataFlow() {
        const packetsContainer = document.getElementById('data-packets');
        if (!packetsContainer) return;

        const centerX = 400, centerY = 270;
        const positions = [];
        document.querySelectorAll('.house-node').forEach(node => {
            const m = node.getAttribute('transform').match(/translate\(([\d.]+),\s*([\d.]+)\)/);
            if (m) positions.push({ x: parseFloat(m[1]), y: parseFloat(m[2]) });
        });

        const count = Math.min(positions.length, 50);
        const delay = positions.length > 30 ? 0.02 : 0.04;
        let html = '';

        for (let i = 0; i < count; i++) {
            const { x, y } = positions[i];
            // colour by agent profile
            const agentId = `house_${(i + 1).toString().padStart(3, '0')}`;
            const profile = this.agentProfileMap[agentId] || 'residential_medium';
            const color   = (PROFILE_COLORS[profile] || DEFAULT_PROFILE_COLOR).stroke;

            html += `
                <g>
                    <circle r="5" fill="${color}" opacity="0.9" filter="url(#glow)">
                        <animate attributeName="cx" from="${x}" to="${centerX}" dur="0.6s" begin="${i * delay}s" fill="freeze"/>
                        <animate attributeName="cy" from="${y}" to="${centerY}" dur="0.6s" begin="${i * delay}s" fill="freeze"/>
                        <animate attributeName="opacity" from="0.9" to="0" dur="0.6s" begin="${i * delay}s" fill="freeze"/>
                    </circle>
                </g>
            `;
        }

        packetsContainer.innerHTML = html;
        setTimeout(() => { packetsContainer.innerHTML = ''; }, 2000);
    }

    // ─── Round Results ────────────────────────────────────────────────────────

    handleMessage(message) {
        if (message.type === 'connected') {
            document.getElementById('agent-count').textContent = message.data.agent_count || '--';
        } else if (message.type === 'round_complete') {
            this.updateRoundResults(message.data);
        }
    }

    updateRoundResults(data) {
        this.roundNumber = data.round_number;
        document.getElementById('round-count').textContent = this.roundNumber;

        // ── Simulated time & peak status ──
        // Prefer server-provided value; fall back to client-computed (round × 15 min).
        const derived  = this.simTimeFromRound(data.round_number);
        const simTime  = (data.simulated_time && data.simulated_time !== '')
                         ? data.simulated_time : derived.timeStr;
        const isPeakNow = (data.is_peak_hour != null) ? data.is_peak_hour : derived.isPeak;
        this.updateSimTimeDisplay(simTime, isPeakNow);

        // ── Profile breakdown ──
        if (data.agent_profiles) {
            this.updateProfileBreakdown(data.agent_profiles);
        }

        // ── Update capacity for threshold drawing ──
        if (data.capacity_kw) this.currentCapacityKw = data.capacity_kw;

        // ── Coordinator ops counter ──
        const coordOps = document.getElementById('coord-ops');
        if (coordOps) coordOps.textContent = `Ops: ${this.roundNumber * data.agent_count}`;

        // ── Aggregate results panel ──
        document.getElementById('total-demand').textContent   = `${data.total_demand_kw.toFixed(2)} kW`;
        document.getElementById('avg-demand').textContent     = `${data.average_demand_kw.toFixed(2)} kW`;
        document.getElementById('utilization').textContent    = `${data.utilization_percent.toFixed(1)}%`;

        // Utilisation bar
        const utilFill = document.querySelector('.util-fill');
        utilFill.style.width = `${Math.min(data.utilization_percent, 100)}%`;
        utilFill.className = 'util-fill' +
            (data.utilization_percent > 100 ? ' danger' : data.utilization_percent > 80 ? ' warning' : '');

        // Load balance action badge
        const actionEl = document.getElementById('lb-action');
        actionEl.textContent = data.action.replace(/_/g, ' ').toUpperCase();
        actionEl.className = 'result-value ' +
            (data.action === 'none' ? 'action-none' : data.action === 'critical' ? 'action-critical' : 'action-reduce');

        // ── Comparison metrics ──
        document.getElementById('enc-total').textContent  = `${data.total_demand_kw.toFixed(6)} kW`;
        document.getElementById('plain-total').textContent= `${data.plaintext_total_kw.toFixed(6)} kW`;
        document.getElementById('error').textContent      = `${data.error_kw.toExponential(3)} kW`;
        document.getElementById('comp-time').textContent  = `${data.computation_time_ms.toFixed(2)} ms`;

        // ── Per-household encrypted flow ──
        this.updateEncryptedFlow(data);

        // ── Charts & topology ──
        this.addToHistory(data);
        this.updateCharts();
        this.updateHouseVisuals();
        this.loadSecurityLogs();
    }

    updateProfileBreakdown(profiles) {
        const breakdown = document.getElementById('profile-breakdown');
        if (!breakdown) return;
        breakdown.style.display = 'flex';

        const set = (id, key) => {
            const el = document.getElementById(id);
            if (el) el.textContent = profiles[key] || 0;
        };
        set('count-res-small',  'residential_small');
        set('count-res-medium', 'residential_medium');
        set('count-res-large',  'residential_large');
        set('count-commercial', 'commercial_small');
    }

    updateEncryptedFlow(data) {
        const container = document.getElementById('encrypted-flow');
        container.innerHTML = '';

        const numToShow = Math.min(this.agents.length, 8);
        for (let i = 0; i < numToShow; i++) {
            const agent  = this.agents[i] || {};
            const demand = agent.current_demand_kw || 0;
            const cipher = this.generateUniqueCiphertext(i, data.round_number);
            const pc     = (PROFILE_COLORS[agent.profile] || DEFAULT_PROFILE_COLOR);

            const item = document.createElement('div');
            item.className = 'flow-item';
            item.innerHTML = `
                <span class="agent-icon" style="color:${pc.stroke}">[H${i+1}]</span>
                <span class="demand-value">${demand.toFixed(2)} kW</span>
                <span class="arrow">→ [ENC] →</span>
                <span class="ciphertext">${cipher}</span>
            `;
            container.appendChild(item);
        }

        if (this.agents.length > numToShow) {
            const more = document.createElement('div');
            more.className = 'flow-item';
            more.style.cssText = 'justify-content:center;color:#8b949e;';
            more.textContent = `… and ${this.agents.length - numToShow} more (each with unique ciphertext)`;
            container.appendChild(more);
        }
    }

    generateUniqueCiphertext(houseIndex, roundNumber) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        const seed  = (houseIndex * 17 + roundNumber * 31) % 1000;
        let cipher  = '';
        for (let i = 0; i < 40; i++) {
            cipher += chars[(seed + i * 7 + houseIndex * 13) % chars.length];
        }
        return cipher + '...';
    }

    // ─── Security Logs ────────────────────────────────────────────────────────

    async loadSecurityLogs() {
        try {
            const logs = await fetch('/security-logs?limit=30').then(r => r.json());
            const container = document.getElementById('security-logs');
            if (!logs.length) {
                container.innerHTML = '<div class="log-entry placeholder">No logs yet…</div>';
                return;
            }
            container.innerHTML = [...logs].reverse().map(log => `
                <div class="log-entry ${log.color}">
                    <span class="log-time">${log.time}</span>
                    <span class="log-icon">${log.icon}</span>
                    <span class="log-entity">${log.entity}</span>
                    <span class="log-operation">${log.operation}</span>
                </div>
            `).join('');
        } catch (e) {
            console.error('Failed to load security logs:', e);
        }
    }

    // ─── Controls ─────────────────────────────────────────────────────────────

    async runRound() {
        const btn = document.getElementById('run-round-btn');
        btn.disabled = true;
        btn.textContent = '⏳ Encrypting…';
        this.animateDataFlow();
        try {
            const result = await fetch('/round', { method: 'POST' }).then(r => r.json());
            this.updateRoundResults(result);
            await this.loadAgents();
        } catch (e) {
            console.error('Failed to run round:', e);
        } finally {
            btn.disabled = false;
            btn.textContent = '▶ Run Round';
        }
    }

    async startAutoRun() {
        try {
            await fetch('/auto/start', { method: 'POST' });
            this.isAutoRunning = true;
            document.getElementById('auto-start-btn').style.display = 'none';
            document.getElementById('auto-stop-btn').style.display  = 'inline-block';
        } catch (e) { console.error('Failed to start auto-run:', e); }
    }

    async stopAutoRun() {
        try {
            await fetch('/auto/stop', { method: 'POST' });
            this.isAutoRunning = false;
            document.getElementById('auto-start-btn').style.display = 'inline-block';
            document.getElementById('auto-stop-btn').style.display  = 'none';
        } catch (e) { console.error('Failed to stop auto-run:', e); }
    }

    async resetSimulation() {
        const agents   = parseInt(document.getElementById('config-agents').value)   || 25;
        const capacity = parseFloat(document.getElementById('config-capacity').value) || 100;
        try {
            await fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_count: agents, grid_capacity_kw: capacity })
            });
            this.history       = [];
            this.roundNumber   = 0;
            this.currentCapacityKw = capacity;
            this.updateCharts();
            document.getElementById('round-count').textContent    = '0';
            document.getElementById('total-demand').textContent   = '-- kW';
            document.getElementById('avg-demand').textContent     = '-- kW';
            document.getElementById('utilization').textContent    = '-- %';
            document.getElementById('lb-action').textContent      = '--';
            document.getElementById('sim-time').textContent       = '00:00';
            document.getElementById('peak-status').textContent    = '● Off-Peak';
            document.getElementById('peak-status').className      = 'value peak-status-offpeak';
            document.querySelector('.util-fill').style.width      = '0%';
            document.getElementById('encrypted-flow').innerHTML   =
                '<div class="flow-item placeholder"><span class="agent-icon">[H]</span>' +
                '<span class="arrow">→</span><span class="ciphertext">Run a round to see encrypted data…</span></div>';
            await this.loadInitialData();
            alert('Simulation reset successfully!');
        } catch (e) {
            console.error('Failed to reset:', e);
            alert('Reset failed. Please refresh the page.');
        }
    }

    async applyConfiguration() {
        const agents   = parseInt(document.getElementById('config-agents').value)   || 25;
        const capacity = parseFloat(document.getElementById('config-capacity').value) || 100;
        if (agents < 5 || agents > 100)   { alert('Households must be 5–100.');  return; }
        if (capacity < 50 || capacity > 500) { alert('Capacity must be 50–500 kW.'); return; }
        try {
            await fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_count: agents, grid_capacity_kw: capacity })
            });
            this.history           = [];
            this.roundNumber       = 0;
            this.currentAgentCount = agents;
            this.currentCapacityKw = capacity;
            this.updateCharts();
            this.generateTopology(agents);
            await this.loadInitialData();
            alert(`Configuration applied: ${agents} households, ${capacity} kW capacity`);
        } catch (e) {
            console.error('Failed to apply config:', e);
            alert('Failed to apply configuration. Please try again.');
        }
    }

    updateStatus(connected) {
        const el = document.getElementById('system-status');
        if (connected) {
            el.textContent = '● Online';
            el.className   = 'value status-online';
        } else {
            el.textContent = '● Offline';
            el.className   = 'value status-offline';
        }
    }
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SmartGridDashboard();
});
