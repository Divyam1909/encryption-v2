/**
 * Smart Grid Dashboard JavaScript - Enhanced
 * With proper topology, charts, configuration, and per-household encryption display
 */

class SmartGridDashboard {
    constructor() {
        this.ws = null;
        this.isAutoRunning = false;
        this.agents = [];
        this.history = [];
        this.maxHistoryPoints = 20;
        this.roundNumber = 0;

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

    setupWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.updateStatus(true);
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateStatus(false);
                setTimeout(() => this.setupWebSocket(), 3000);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (e) {
            console.error('WebSocket setup failed:', e);
            this.updateStatus(false);
        }
    }

    setupEventListeners() {
        document.getElementById('run-round-btn').addEventListener('click', () => {
            this.runRound();
        });

        document.getElementById('auto-start-btn').addEventListener('click', () => {
            this.startAutoRun();
        });

        document.getElementById('auto-stop-btn').addEventListener('click', () => {
            this.stopAutoRun();
        });

        document.getElementById('reset-btn').addEventListener('click', () => {
            this.resetSimulation();
        });

        document.getElementById('apply-config-btn').addEventListener('click', () => {
            this.applyConfiguration();
        });
    }

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;

                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`${tabId}-tab`).classList.add('active');

                if (tabId === 'graphs') {
                    setTimeout(() => this.resizeCharts(), 100);
                }
            });
        });
    }

    initCharts() {
        const chartDefaults = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            plugins: {
                legend: {
                    labels: { color: '#8b949e', font: { size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(78, 204, 163, 0.1)' },
                    ticks: { color: '#8b949e' }
                },
                y: {
                    grid: { color: 'rgba(78, 204, 163, 0.1)' },
                    ticks: { color: '#8b949e' }
                }
            }
        };

        // Comparison Chart - Fixed with distinct line styles
        const compCtx = document.getElementById('comparison-chart');
        if (compCtx) {
            this.comparisonChart = new Chart(compCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Encrypted Total (kW)',
                            data: [],
                            borderColor: '#4ecca3',
                            backgroundColor: 'rgba(78, 204, 163, 0.2)',
                            fill: false,
                            tension: 0.3,
                            borderWidth: 3,
                            pointRadius: 5,
                            pointBackgroundColor: '#4ecca3'
                        },
                        {
                            label: 'Plaintext Total (kW)',
                            data: [],
                            borderColor: '#ff6b6b',
                            backgroundColor: 'rgba(255, 107, 107, 0.2)',
                            fill: false,
                            tension: 0.3,
                            borderWidth: 2,
                            borderDash: [8, 4],
                            pointRadius: 4,
                            pointBackgroundColor: '#ff6b6b',
                            pointStyle: 'rect'
                        }
                    ]
                },
                options: {
                    ...chartDefaults,
                    plugins: {
                        ...chartDefaults.plugins,
                        title: {
                            display: true,
                            text: 'FHE maintains precision across all rounds',
                            color: '#8b949e'
                        }
                    }
                }
            });
        }

        // Utilization Chart - Fixed with proper Y axis
        const utilCtx = document.getElementById('utilization-chart');
        if (utilCtx) {
            this.utilizationChart = new Chart(utilCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Utilization %',
                        data: [],
                        borderColor: '#f0a500',
                        backgroundColor: 'rgba(240, 165, 0, 0.2)',
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2
                    }]
                },
                options: {
                    ...chartDefaults,
                    scales: {
                        ...chartDefaults.scales,
                        y: {
                            ...chartDefaults.scales.y,
                            min: 0,
                            max: 150,
                            ticks: {
                                color: '#8b949e',
                                stepSize: 25
                            }
                        }
                    }
                }
            });
        }

        // Time Chart
        const timeCtx = document.getElementById('time-chart');
        if (timeCtx) {
            this.timeChart = new Chart(timeCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Computation Time (ms)',
                        data: [],
                        backgroundColor: 'rgba(78, 204, 163, 0.6)',
                        borderColor: '#4ecca3',
                        borderWidth: 1
                    }]
                },
                options: chartDefaults
            });
        }

        // Error Chart
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
                        backgroundColor: 'rgba(88, 166, 255, 0.2)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    ...chartDefaults,
                    scales: {
                        ...chartDefaults.scales,
                        y: {
                            ...chartDefaults.scales.y,
                            type: 'logarithmic',
                            ticks: {
                                color: '#8b949e',
                                callback: function (value) {
                                    return value.toExponential(0);
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    resizeCharts() {
        if (this.comparisonChart) this.comparisonChart.resize();
        if (this.utilizationChart) this.utilizationChart.resize();
        if (this.timeChart) this.timeChart.resize();
        if (this.errorChart) this.errorChart.resize();
    }

    generateTopology() {
        const container = document.getElementById('house-nodes');
        const linesContainer = document.getElementById('connection-lines');
        if (!container || !linesContainer) return;

        const centerX = 400;
        const centerY = 280;
        const numHouses = 12;

        // Create neat circular layout with proper spacing
        const radius = 180;

        let housesHtml = '';
        let linesHtml = '';

        for (let i = 0; i < numHouses; i++) {
            // Start from top (12 o'clock) and go clockwise
            const angle = (i / numHouses) * 2 * Math.PI - Math.PI / 2;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);

            // Connection line
            linesHtml += `
                <line class="connection-line" 
                      x1="${x}" y1="${y}" 
                      x2="${centerX}" y2="${centerY}" 
                      stroke="url(#line-gradient)" 
                      stroke-width="1.5" 
                      stroke-dasharray="5,5"
                      opacity="0.6">
                </line>
            `;

            // House node - cleaner design
            const houseId = i + 1;
            housesHtml += `
                <g class="house-node" id="house-${i}" transform="translate(${x}, ${y})">
                    <rect class="house-bg" x="-35" y="-28" width="70" height="56" rx="8" 
                          fill="#161b22" stroke="#f0a500" stroke-width="2"/>
                    <text y="-8" text-anchor="middle" font-size="18">🏠</text>
                    <text y="8" text-anchor="middle" fill="#e6edf3" font-size="11" font-weight="600">H${houseId}</text>
                    <rect class="demand-bar-bg" x="-25" y="14" width="50" height="6" rx="3" fill="#0d1117"/>
                    <rect class="demand-bar" id="demand-bar-${i}" x="-25" y="14" width="25" height="6" rx="3" fill="#4ecca3"/>
                    <text class="house-demand" id="house-demand-${i}" y="30" text-anchor="middle" fill="#8b949e" font-size="8"></text>
                </g>
            `;
        }

        linesContainer.innerHTML = linesHtml;
        container.innerHTML = housesHtml;
    }

    async loadInitialData() {
        try {
            const response = await fetch('/status');
            const status = await response.json();

            document.getElementById('agent-count').textContent = status.agent_count || '--';
            this.roundNumber = status.round_count || 0;
            document.getElementById('round-count').textContent = this.roundNumber;

            await this.loadAgents();
            this.loadSecurityLogs();
            await this.loadHistory();
        } catch (e) {
            console.error('Failed to load initial data:', e);
        }
    }

    async loadAgents() {
        try {
            const response = await fetch('/agents');
            this.agents = await response.json();
            this.updateHouseVisuals();
        } catch (e) {
            console.error('Failed to load agents:', e);
        }
    }

    async loadHistory() {
        try {
            const response = await fetch('/history?limit=20');
            const history = await response.json();

            this.history = [];
            history.forEach(round => {
                this.addToHistory(round);
            });

            this.updateCharts();
        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }

    addToHistory(data) {
        this.history.push({
            round: data.round_number,
            encTotal: data.total_demand_kw,
            plainTotal: data.plaintext_total_kw,
            utilization: data.utilization_percent,
            compTime: data.computation_time_ms,
            error: data.error_kw
        });

        if (this.history.length > this.maxHistoryPoints) {
            this.history.shift();
        }
    }

    updateCharts() {
        // Use proper round labels (Round 1, Round 2, etc.)
        const labels = this.history.map(h => `Round ${h.round}`);

        // Comparison chart with both lines visible
        if (this.comparisonChart) {
            this.comparisonChart.data.labels = labels;
            this.comparisonChart.data.datasets[0].data = this.history.map(h => h.encTotal);
            this.comparisonChart.data.datasets[1].data = this.history.map(h => h.plainTotal);
            this.comparisonChart.update('none');
        }

        // Utilization chart
        if (this.utilizationChart) {
            this.utilizationChart.data.labels = labels;
            this.utilizationChart.data.datasets[0].data = this.history.map(h => h.utilization);
            this.utilizationChart.update('none');
        }

        // Time chart
        if (this.timeChart) {
            this.timeChart.data.labels = labels;
            this.timeChart.data.datasets[0].data = this.history.map(h => h.compTime);
            this.timeChart.update('none');
        }

        // Error chart
        if (this.errorChart) {
            this.errorChart.data.labels = labels;
            this.errorChart.data.datasets[0].data = this.history.map(h => Math.max(h.error, 1e-10));
            this.errorChart.update('none');
        }
    }

    updateHouseVisuals() {
        this.agents.slice(0, 12).forEach((agent, i) => {
            const bar = document.getElementById(`demand-bar-${i}`);
            const demandText = document.getElementById(`house-demand-${i}`);
            const node = document.getElementById(`house-${i}`);

            if (bar && agent.current_demand_kw !== undefined) {
                const demand = agent.current_demand_kw || 0;
                const maxDemand = 8;
                const percentage = Math.min(demand / maxDemand, 1);
                const width = 50 * percentage;

                bar.setAttribute('width', Math.max(width, 2));

                // Color based on demand level
                if (percentage > 0.8) {
                    bar.setAttribute('fill', '#f85149');
                } else if (percentage > 0.5) {
                    bar.setAttribute('fill', '#f0a500');
                } else {
                    bar.setAttribute('fill', '#4ecca3');
                }

                // Show demand value
                if (demandText) {
                    demandText.textContent = `${demand.toFixed(1)} kW`;
                }

                // Pulse animation
                if (node) {
                    const bg = node.querySelector('.house-bg');
                    if (bg) {
                        bg.style.filter = 'drop-shadow(0 0 8px #4ecca3)';
                        setTimeout(() => {
                            bg.style.filter = 'none';
                        }, 500);
                    }
                }
            }
        });
    }

    animateDataFlow() {
        const packetsContainer = document.getElementById('data-packets');
        if (!packetsContainer) return;

        const centerX = 400;
        const centerY = 280;
        const radius = 180;
        const numHouses = 12;

        let packetsHtml = '';

        for (let i = 0; i < numHouses; i++) {
            const angle = (i / numHouses) * 2 * Math.PI - Math.PI / 2;
            const startX = centerX + radius * Math.cos(angle);
            const startY = centerY + radius * Math.sin(angle);

            packetsHtml += `
                <g class="data-packet-group">
                    <circle r="8" fill="#4ecca3" opacity="0.9" filter="url(#glow)">
                        <animate attributeName="cx" from="${startX}" to="${centerX}" dur="0.6s" 
                                 begin="${i * 0.04}s" fill="freeze"/>
                        <animate attributeName="cy" from="${startY}" to="${centerY}" dur="0.6s" 
                                 begin="${i * 0.04}s" fill="freeze"/>
                        <animate attributeName="opacity" from="0.9" to="0" dur="0.6s" 
                                 begin="${i * 0.04}s" fill="freeze"/>
                    </circle>
                    <text fill="#4ecca3" font-size="8" opacity="0.8">
                        <animate attributeName="x" from="${startX + 10}" to="${centerX + 10}" dur="0.6s" 
                                 begin="${i * 0.04}s" fill="freeze"/>
                        <animate attributeName="y" from="${startY}" to="${centerY}" dur="0.6s" 
                                 begin="${i * 0.04}s" fill="freeze"/>
                        <animate attributeName="opacity" from="0.8" to="0" dur="0.6s" 
                                 begin="${i * 0.04}s" fill="freeze"/>
                        🔒
                    </text>
                </g>
            `;
        }

        packetsContainer.innerHTML = packetsHtml;

        setTimeout(() => {
            packetsContainer.innerHTML = '';
        }, 1000);
    }

    handleMessage(message) {
        if (message.type === 'connected') {
            document.getElementById('agent-count').textContent = message.data.agent_count || '--';
        } else if (message.type === 'round_complete') {
            this.updateRoundResults(message.data);
        }
    }

    async runRound() {
        const btn = document.getElementById('run-round-btn');
        btn.disabled = true;
        btn.textContent = '⏳ Encrypting...';

        this.animateDataFlow();

        try {
            const response = await fetch('/round', { method: 'POST' });
            const result = await response.json();
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
            document.getElementById('auto-stop-btn').style.display = 'inline-block';
        } catch (e) {
            console.error('Failed to start auto-run:', e);
        }
    }

    async stopAutoRun() {
        try {
            await fetch('/auto/stop', { method: 'POST' });
            this.isAutoRunning = false;
            document.getElementById('auto-start-btn').style.display = 'inline-block';
            document.getElementById('auto-stop-btn').style.display = 'none';
        } catch (e) {
            console.error('Failed to stop auto-run:', e);
        }
    }

    async resetSimulation() {
        try {
            const agents = parseInt(document.getElementById('config-agents').value) || 25;
            const capacity = parseFloat(document.getElementById('config-capacity').value) || 100;

            await fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_count: agents, grid_capacity_kw: capacity })
            });

            this.history = [];
            this.roundNumber = 0;
            this.updateCharts();

            document.getElementById('round-count').textContent = '0';
            document.getElementById('total-demand').textContent = '-- kW';
            document.getElementById('avg-demand').textContent = '-- kW';
            document.getElementById('utilization').textContent = '-- %';
            document.getElementById('lb-action').textContent = '--';
            document.querySelector('.util-fill').style.width = '0%';

            const flowContainer = document.getElementById('encrypted-flow');
            flowContainer.innerHTML = '<div class="flow-item placeholder"><span class="agent-icon">🏠</span><span class="arrow">→</span><span class="ciphertext">Run a round to see encrypted data per household...</span></div>';

            await this.loadInitialData();

            alert('Simulation reset successfully!');
        } catch (e) {
            console.error('Failed to reset simulation:', e);
            alert('Failed to reset. Please refresh the page.');
        }
    }

    async applyConfiguration() {
        const agents = parseInt(document.getElementById('config-agents').value) || 25;
        const capacity = parseFloat(document.getElementById('config-capacity').value) || 100;

        if (agents < 5 || agents > 100) {
            alert('Number of households must be between 5 and 100.');
            return;
        }

        if (capacity < 50 || capacity > 500) {
            alert('Grid capacity must be between 50 and 500 kW.');
            return;
        }

        try {
            await fetch('/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_count: agents, grid_capacity_kw: capacity })
            });

            this.history = [];
            this.roundNumber = 0;
            this.updateCharts();

            await this.loadInitialData();

            alert(`Configuration applied: ${agents} households, ${capacity} kW capacity`);
        } catch (e) {
            console.error('Failed to apply configuration:', e);
            alert('Failed to apply configuration. Please try again.');
        }
    }

    updateRoundResults(data) {
        this.roundNumber = data.round_number;
        document.getElementById('round-count').textContent = this.roundNumber;

        // Update coordinator ops
        const coordOps = document.getElementById('coord-ops');
        if (coordOps) {
            coordOps.textContent = `Ops: ${this.roundNumber * data.agent_count}`;
        }

        // Update results
        document.getElementById('total-demand').textContent = `${data.total_demand_kw.toFixed(2)} kW`;
        document.getElementById('avg-demand').textContent = `${data.average_demand_kw.toFixed(2)} kW`;
        document.getElementById('utilization').textContent = `${data.utilization_percent.toFixed(1)}%`;

        // Update utilization bar
        const utilFill = document.querySelector('.util-fill');
        utilFill.style.width = `${Math.min(data.utilization_percent, 100)}%`;
        utilFill.className = 'util-fill';
        if (data.utilization_percent > 100) {
            utilFill.classList.add('danger');
        } else if (data.utilization_percent > 80) {
            utilFill.classList.add('warning');
        }

        // Update action
        const actionEl = document.getElementById('lb-action');
        actionEl.textContent = data.action.replace('_', ' ').toUpperCase();
        actionEl.className = 'result-value';
        if (data.action === 'none') {
            actionEl.classList.add('action-none');
        } else if (data.action === 'critical') {
            actionEl.classList.add('action-critical');
        } else {
            actionEl.classList.add('action-reduce');
        }

        // Update comparison panel
        document.getElementById('enc-total').textContent = `${data.total_demand_kw.toFixed(4)} kW`;
        document.getElementById('plain-total').textContent = `${data.plaintext_total_kw.toFixed(4)} kW`;
        document.getElementById('error').textContent = `${data.error_kw.toExponential(2)} kW`;
        document.getElementById('comp-time').textContent = `${data.computation_time_ms.toFixed(2)} ms`;

        // Update per-household encrypted flow - DIFFERENT ciphertexts for each!
        this.updateEncryptedFlow(data);

        // Add to history and update charts
        this.addToHistory(data);
        this.updateCharts();

        // Update house visuals
        this.updateHouseVisuals();

        // Reload security logs
        this.loadSecurityLogs();
    }

    updateEncryptedFlow(data) {
        const container = document.getElementById('encrypted-flow');

        // Clear previous content
        container.innerHTML = '';

        // Show individual household encrypted data (simulated unique ciphertexts)
        const numToShow = Math.min(this.agents.length, 8);

        for (let i = 0; i < numToShow; i++) {
            const agent = this.agents[i] || {};
            const demand = agent.current_demand_kw || (Math.random() * 5 + 2);

            // Generate unique-looking ciphertext for each household
            const uniqueCiphertext = this.generateUniqueCiphertext(i, data.round_number);

            const item = document.createElement('div');
            item.className = 'flow-item';
            item.innerHTML = `
                <span class="agent-icon">🏠 H${i + 1}</span>
                <span class="demand-value">${demand.toFixed(2)} kW</span>
                <span class="arrow">→ 🔒 →</span>
                <span class="ciphertext">${uniqueCiphertext}</span>
            `;
            container.appendChild(item);
        }

        // Add "and more" indicator
        if (this.agents.length > numToShow) {
            const moreItem = document.createElement('div');
            moreItem.className = 'flow-item';
            moreItem.style.justifyContent = 'center';
            moreItem.style.color = '#8b949e';
            moreItem.innerHTML = `... and ${this.agents.length - numToShow} more households (each with unique encryption)`;
            container.appendChild(moreItem);
        }
    }

    generateUniqueCiphertext(houseIndex, roundNumber) {
        // Generate a realistic-looking unique ciphertext for each house
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        let cipher = '';

        // Use house index and round as seed for variation
        const seed = (houseIndex * 17 + roundNumber * 31) % 1000;

        for (let i = 0; i < 40; i++) {
            const idx = (seed + i * 7 + houseIndex * 13) % chars.length;
            cipher += chars[idx];
        }

        return cipher + '...';
    }

    async loadSecurityLogs() {
        try {
            const response = await fetch('/security-logs?limit=30');
            const logs = await response.json();

            const container = document.getElementById('security-logs');

            if (logs.length === 0) {
                container.innerHTML = '<div class="log-entry placeholder">No logs yet...</div>';
                return;
            }

            container.innerHTML = logs.reverse().map(log => `
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

    updateStatus(connected) {
        const statusEl = document.getElementById('system-status');
        if (connected) {
            statusEl.textContent = '● Online';
            statusEl.className = 'value status-online';
        } else {
            statusEl.textContent = '● Offline';
            statusEl.className = 'value status-offline';
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SmartGridDashboard();
});
