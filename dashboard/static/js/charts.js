/**
 * Chart.js Configuration and Management
 * Handles creation and updating of all dashboard charts
 */

// Chart color palette matching dark theme
const CHART_COLORS = {
    profit: 'rgba(74, 222, 128, 0.8)',
    profitBg: 'rgba(74, 222, 128, 0.1)',
    loss: 'rgba(239, 68, 68, 0.8)',
    lossBg: 'rgba(239, 68, 68, 0.1)',
    neutral: 'rgba(59, 130, 246, 0.8)',
    neutralBg: 'rgba(59, 130, 246, 0.1)',
    warning: 'rgba(245, 158, 11, 0.8)',
    warningBg: 'rgba(245, 158, 11, 0.1)',
    grid: 'rgba(68, 68, 68, 0.5)',
    text: '#ffffff',
    textSecondary: '#b0b0b0'
};

// Default Chart.js options for dark theme
const DEFAULT_CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
        legend: {
            labels: {
                color: CHART_COLORS.text,
                font: { size: 12, weight: '600' },
                padding: 15
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: CHART_COLORS.text,
            bodyColor: CHART_COLORS.textSecondary,
            borderColor: CHART_COLORS.grid,
            borderWidth: 1
        }
    },
    scales: {
        x: {
            ticks: { color: CHART_COLORS.textSecondary },
            grid: { color: CHART_COLORS.grid },
            border: { color: CHART_COLORS.grid }
        },
        y: {
            ticks: { color: CHART_COLORS.textSecondary },
            grid: { color: CHART_COLORS.grid },
            border: { color: CHART_COLORS.grid }
        }
    }
};

/**
 * Create Equity Curve Chart
 */
function createEquityCurveChart() {
    const canvas = document.getElementById('equityCurveChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Demo data
    const dates = generateDateLabels(30);
    const equityData = generateEquityData(10000, 30);

    chartInstances.equityCurve = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Equity',
                data: equityData,
                borderColor: CHART_COLORS.neutral,
                backgroundColor: CHART_COLORS.neutralBg,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: CHART_COLORS.neutral,
                pointBorderColor: CHART_COLORS.text,
                pointHoverRadius: 5
            }]
        },
        options: {
            ...DEFAULT_CHART_OPTIONS,
            plugins: {
                ...DEFAULT_CHART_OPTIONS.plugins,
                filler: {
                    propagate: true
                }
            },
            scales: {
                ...DEFAULT_CHART_OPTIONS.scales,
                y: {
                    ...DEFAULT_CHART_OPTIONS.scales.y,
                    ticks: {
                        ...DEFAULT_CHART_OPTIONS.scales.y.ticks,
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });

    // Update chart with real data
    updateEquityCurveChart();
}

/**
 * Update Equity Curve Chart with real data
 */
function updateEquityCurveChart() {
    fetch(`${DASHBOARD_CONFIG.apiBaseUrl}/equity-curve?limit=50`)
        .then(response => response.json())
        .then(data => {
            if (chartInstances.equityCurve && data.data && data.data.length > 0) {
                const labels = data.data.map(d => formatDate(d.timestamp));
                const equity = data.data.map(d => d.equity);

                chartInstances.equityCurve.data.labels = labels;
                chartInstances.equityCurve.data.datasets[0].data = equity;
                chartInstances.equityCurve.update();
            }
        })
        .catch(error => console.error('Error updating equity curve:', error));
}

/**
 * Create Trade Distribution Chart
 */
function createTradeDistributionChart() {
    const canvas = document.getElementById('tradeDistributionChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Demo data
    const trades = generateTradeData(50);
    const bins = createPnlBins(trades);

    chartInstances.tradeDistribution = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: bins.labels,
            datasets: [{
                label: 'Number of Trades',
                data: bins.counts,
                backgroundColor: bins.colors,
                borderColor: bins.borderColors,
                borderWidth: 1
            }]
        },
        options: {
            ...DEFAULT_CHART_OPTIONS,
            indexAxis: 'x',
            scales: {
                ...DEFAULT_CHART_OPTIONS.scales,
                y: {
                    ...DEFAULT_CHART_OPTIONS.scales.y,
                    beginAtZero: true,
                    ticks: {
                        ...DEFAULT_CHART_OPTIONS.scales.y.ticks,
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Create Win/Loss Ratio Chart
 */
function createWinLossChart() {
    const canvas = document.getElementById('winLossChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Demo data: 65% win rate
    const winRate = 65;
    const lossRate = 100 - winRate;

    chartInstances.winLoss = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Winning Trades', 'Losing Trades'],
            datasets: [{
                data: [winRate, lossRate],
                backgroundColor: [
                    CHART_COLORS.profit,
                    CHART_COLORS.loss
                ],
                borderColor: [
                    CHART_COLORS.profit,
                    CHART_COLORS.loss
                ],
                borderWidth: 2
            }]
        },
        options: {
            ...DEFAULT_CHART_OPTIONS,
            plugins: {
                ...DEFAULT_CHART_OPTIONS.plugins,
                legend: {
                    ...DEFAULT_CHART_OPTIONS.plugins.legend,
                    position: 'bottom'
                }
            }
        }
    });

    // Update with real data
    updateWinLossChart();
}

/**
 * Update Win/Loss Chart with real data
 */
function updateWinLossChart() {
    if (chartInstances.winLoss && currentMetrics.win_rate !== undefined) {
        const winRate = currentMetrics.win_rate || 0;
        const lossRate = 100 - winRate;

        chartInstances.winLoss.data.datasets[0].data = [winRate, lossRate];
        chartInstances.winLoss.update();
    }
}

/**
 * Create Daily Performance Chart
 */
function createDailyPerformanceChart() {
    const canvas = document.getElementById('dailyPerformanceChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Demo data
    const days = generateDateLabels(7);
    const returns = generateDailyReturns(7);

    chartInstances.dailyPerformance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: days,
            datasets: [{
                label: 'Daily P&L',
                data: returns,
                backgroundColor: returns.map(r => r >= 0 ? CHART_COLORS.profit : CHART_COLORS.loss),
                borderColor: returns.map(r => r >= 0 ? CHART_COLORS.profit : CHART_COLORS.loss),
                borderWidth: 1
            }]
        },
        options: {
            ...DEFAULT_CHART_OPTIONS,
            scales: {
                ...DEFAULT_CHART_OPTIONS.scales,
                y: {
                    ...DEFAULT_CHART_OPTIONS.scales.y,
                    ticks: {
                        ...DEFAULT_CHART_OPTIONS.scales.y.ticks,
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

/**
 * Helper: Generate date labels
 */
function generateDateLabels(days) {
    const labels = [];
    const now = new Date();
    for (let i = days; i > 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        labels.push(formatDate(date));
    }
    return labels;
}

/**
 * Helper: Generate equity data
 */
function generateEquityData(initial, days) {
    const data = [initial];
    let current = initial;
    for (let i = 1; i < days; i++) {
        const change = (Math.random() - 0.48) * 200; // Slight upward bias
        current = Math.max(current + change, initial * 0.95); // Prevent too large losses
        data.push(current);
    }
    return data;
}

/**
 * Helper: Generate daily returns
 */
function generateDailyReturns(days) {
    const returns = [];
    for (let i = 0; i < days; i++) {
        returns.push((Math.random() - 0.4) * 500);
    }
    return returns;
}

/**
 * Helper: Generate trade data
 */
function generateTradeData(count) {
    const trades = [];
    for (let i = 0; i < count; i++) {
        trades.push({
            pnl: (Math.random() - 0.45) * 500,
            id: i
        });
    }
    return trades;
}

/**
 * Helper: Create P&L bins for histogram
 */
function createPnlBins(trades) {
    const bins = {
        '< -200': 0,
        '-200 to -100': 0,
        '-100 to 0': 0,
        '0 to 100': 0,
        '100 to 200': 0,
        '> 200': 0
    };

    trades.forEach(trade => {
        const pnl = trade.pnl || 0;
        if (pnl < -200) bins['< -200']++;
        else if (pnl < -100) bins['-200 to -100']++;
        else if (pnl < 0) bins['-100 to 0']++;
        else if (pnl < 100) bins['0 to 100']++;
        else if (pnl < 200) bins['100 to 200']++;
        else bins['> 200']++;
    });

    const labels = Object.keys(bins);
    const counts = Object.values(bins);
    const colors = labels.map((label, idx) => {
        if (idx <= 2) return CHART_COLORS.lossBg;
        if (idx <= 4) return CHART_COLORS.profitBg;
        return CHART_COLORS.profitBg;
    });

    return {
        labels,
        counts,
        colors,
        borderColors: labels.map((label, idx) => {
            if (idx <= 2) return CHART_COLORS.loss;
            if (idx <= 4) return CHART_COLORS.profit;
            return CHART_COLORS.profit;
        })
    };
}

/**
 * Helper: Format date for display
 */
function formatDate(date) {
    if (typeof date === 'string') {
        date = new Date(date);
    }
    if (!(date instanceof Date)) return '';

    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    return `${month}-${day} ${hour}:00`;
}

/**
 * Destroy and recreate a chart
 */
function recreateChart(chartKey) {
    if (chartInstances[chartKey]) {
        chartInstances[chartKey].destroy();
        delete chartInstances[chartKey];
    }
}

/**
 * Update all charts with fresh data
 */
function refreshAllCharts() {
    updateEquityCurveChart();
    updateWinLossChart();
    // Other charts would be updated similarly
}

// Update charts when metrics change
setInterval(() => {
    if (Object.keys(chartInstances).length > 0) {
        refreshAllCharts();
    }
}, DASHBOARD_CONFIG.refreshInterval * 2); // Update charts less frequently than metrics
