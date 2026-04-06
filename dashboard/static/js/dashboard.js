/**
 * Dashboard Real-Time Updates
 * Handles fetching data from API and updating DOM in real-time
 */

// Global state
let refreshInterval = null;
let currentMetrics = {};
let previousMetrics = {};

/**
 * Initialize dashboard on page load
 */
function initializeCharts() {
    console.log('Initializing charts...');
    createEquityCurveChart();
    createTradeDistributionChart();
    createWinLossChart();
    createDailyPerformanceChart();
}

/**
 * Start auto-refresh of all data
 */
function startAutoRefresh() {
    console.log('Starting auto-refresh with interval:', DASHBOARD_CONFIG.refreshInterval);

    // Initial load
    updateAllMetrics();

    // Set up periodic refresh
    refreshInterval = setInterval(() => {
        // Only update if page is visible
        if (!document.hidden) {
            updateAllMetrics();
        }
    }, DASHBOARD_CONFIG.refreshInterval);

    // Update current time
    setInterval(updateCurrentTime, 1000);
}

/**
 * Update all dashboard metrics
 */
function updateAllMetrics() {
    updateMetrics();
    updatePositions();
    updateSignals();
    updateTrades();
    // Don't load logs every update - only manually
}

/**
 * Update main metrics cards
 */
function updateMetrics() {
    fetch(`${DASHBOARD_CONFIG.apiBaseUrl}/metrics`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            previousMetrics = { ...currentMetrics };
            currentMetrics = data;

            // Update metric cards
            updateElement('metric-balance', formatCurrency(data.balance));
            updateElement('metric-equity', formatCurrency(data.equity));
            updateElement('metric-pnl', formatCurrency(data.total_pnl));
            updateElement('metric-pnl-pct', formatPercentage(data.pnl_pct));
            updateElement('metric-win-rate', formatPercentage(data.win_rate));
            updateElement('metric-total-trades', data.trades_total.toString());
            updateElement('metric-drawdown', formatPercentage(Math.abs(data.max_drawdown_pct)));
            updateElement('metric-open-trades', data.open_trades.toString());
            updateElement('metric-max-trades', data.max_open_trades.toString());
            updateElement('metric-profit-factor', data.profit_factor.toFixed(2));
            updateElement('metric-daily-loss', formatCurrency(data.daily_loss));
            updateElement('metric-daily-limit', formatCurrency(data.max_daily_loss));
            updateElement('metric-avg-win', formatCurrency(0)); // Placeholder
            updateElement('metric-avg-loss', formatCurrency(0)); // Placeholder

            // Update bot status
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.getElementById('status-text');
            const isOnline = data.bot_status === 'online';

            statusDot.classList.remove('online', 'offline');
            statusDot.classList.add(isOnline ? 'online' : 'offline');
            statusText.textContent = isOnline ? 'Online' : 'Offline';

            // Update progress bars
            if (data.max_open_trades > 0) {
                const tradeProgress = (data.open_trades / data.max_open_trades) * 100;
                updateProgressBar('progress-trades', tradeProgress);
            }

            if (data.trades_total > 0) {
                updateProgressBar('progress-win-rate', data.win_rate);
            }

            // Update P&L display color
            const pnlElement = document.getElementById('metric-pnl-display');
            if (data.total_pnl > 0) {
                pnlElement.style.color = 'var(--accent-profit)';
                pnlElement.textContent = `+${formatCurrency(data.total_pnl)} (+${data.pnl_pct.toFixed(2)}%)`;
            } else if (data.total_pnl < 0) {
                pnlElement.style.color = 'var(--accent-loss)';
                pnlElement.textContent = `${formatCurrency(data.total_pnl)} (${data.pnl_pct.toFixed(2)}%)`;
            }

            // Update last update time
            updateElement('last-update', new Date().toLocaleTimeString());
        })
        .catch(error => {
            console.error('Error fetching metrics:', error);
            showError(`Failed to fetch metrics: ${error.message}`);
        });
}

/**
 * Update open positions table
 */
function updatePositions() {
    fetch(`${DASHBOARD_CONFIG.apiBaseUrl}/positions`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            const tbody = document.getElementById('positions-tbody');

            if (!data.positions || data.positions.length === 0) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="8" class="text-center">No open positions</td></tr>';
                return;
            }

            tbody.innerHTML = data.positions.map(position => `
                <tr>
                    <td class="${position.type === 'BUY' ? 'buy' : 'sell'}">${position.type}</td>
                    <td>${formatCurrency(position.entry_price)}</td>
                    <td>${position.current_price ? formatCurrency(position.current_price) : 'N/A'}</td>
                    <td>${formatDateTime(position.entry_time)}</td>
                    <td>${position.bars_held || '-'} bars</td>
                    <td class="${position.unrealized_pnl > 0 ? 'profit' : position.unrealized_pnl < 0 ? 'loss' : ''}">
                        ${position.unrealized_pnl ? formatCurrency(position.unrealized_pnl) : 'N/A'}
                    </td>
                    <td>${position.stop_loss ? formatCurrency(position.stop_loss) : 'N/A'}</td>
                    <td>${position.take_profit ? formatCurrency(position.take_profit) : 'N/A'}</td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Error fetching positions:', error);
        });
}

/**
 * Update trading signals display
 */
function updateSignals() {
    fetch(`${DASHBOARD_CONFIG.apiBaseUrl}/signals?limit=5`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            const container = document.getElementById('signals-container');

            if (!data.signals || data.signals.length === 0) {
                container.innerHTML = '<div class="signal-card empty"><p class="text-muted">No signals yet</p></div>';
                return;
            }

            container.innerHTML = data.signals.map(signal => {
                const directionClass = signal.direction.toLowerCase();
                const confidence = (signal.confidence * 100).toFixed(0);

                return `
                    <div class="signal-card">
                        <div class="signal-direction ${directionClass}">${signal.direction}</div>
                        <div class="signal-confidence">
                            Confidence: ${confidence}%
                        </div>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${confidence}%"></div>
                        </div>
                        <div class="signal-time">${formatDateTime(signal.timestamp)}</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted);">
                            ${signal.indicator || 'XGBoost'}
                        </div>
                    </div>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Error fetching signals:', error);
        });
}

/**
 * Update trades table
 */
function updateTrades() {
    const limit = document.getElementById('trades-limit')?.value || 50;
    const offset = tradesPage * tradesPerPage;

    fetch(`${DASHBOARD_CONFIG.apiBaseUrl}/trades?limit=${limit}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            const tbody = document.getElementById('trades-tbody');

            if (!data.trades || data.trades.length === 0) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="10" class="text-center">No trades yet</td></tr>';
                return;
            }

            // Paginate trades
            const start = offset;
            const end = start + tradesPerPage;
            const paginatedTrades = data.trades.slice(start, end);

            tbody.innerHTML = paginatedTrades.map(trade => {
                const pnl = trade.pnl || 0;
                const pnlClass = pnl > 0 ? 'profit' : pnl < 0 ? 'loss' : '';
                const typeClass = trade.type === 'BUY' ? 'buy' : 'sell';

                return `
                    <tr>
                        <td>${trade.id || '-'}</td>
                        <td class="${typeClass}">${trade.type || '-'}</td>
                        <td>${trade.entry_time ? formatDateTime(trade.entry_time) : '-'}</td>
                        <td>${trade.entry_price ? formatCurrency(trade.entry_price) : '-'}</td>
                        <td>${trade.exit_time ? formatDateTime(trade.exit_time) : '-'}</td>
                        <td>${trade.exit_price ? formatCurrency(trade.exit_price) : '-'}</td>
                        <td class="${pnlClass}">${formatCurrency(pnl)}</td>
                        <td class="${pnlClass}">${(trade.pnl_pct || 0).toFixed(2)}%</td>
                        <td>${trade.bars_held || '-'}</td>
                        <td>${trade.status || '-'}</td>
                    </tr>
                `;
            }).join('');

            // Update pagination info
            const totalPages = Math.ceil(data.count / tradesPerPage);
            const pageInfo = document.getElementById('trades-page-info');
            pageInfo.textContent = `Page ${tradesPage + 1} of ${totalPages || 1}`;
        })
        .catch(error => {
            console.error('Error fetching trades:', error);
        });
}

/**
 * Load and display logs
 */
function loadLogs() {
    fetch(`${DASHBOARD_CONFIG.apiBaseUrl}/logs?lines=50`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            const logsElement = document.getElementById('debug-logs');
            logsElement.textContent = data.logs || 'No logs available';
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
        });
}

/**
 * Update current time display
 */
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { hour12: false });
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = timeString;
    }
}

/**
 * Update progress bar width
 */
function updateProgressBar(elementId, percentage) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.width = Math.min(percentage, 100) + '%';
    }
}

/**
 * Update DOM element with animation
 */
function updateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element && element.textContent !== value) {
        element.textContent = value;
        // Add subtle animation
        element.style.opacity = '0.7';
        setTimeout(() => {
            element.style.opacity = '1';
            element.style.transition = 'opacity 300ms ease';
        }, 0);
    }
}

/**
 * Format number as currency
 */
function formatCurrency(value) {
    if (typeof value !== 'number') return '$0.00';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Format number as percentage
 */
function formatPercentage(value) {
    if (typeof value !== 'number') return '0.00%';
    return Math.abs(value).toFixed(2) + '%';
}

/**
 * Format date time
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    } catch {
        return dateStr;
    }
}

/**
 * Show error notification
 */
function showError(message) {
    const toast = document.getElementById('error-toast');
    const messageEl = document.getElementById('error-message');
    messageEl.textContent = message;
    toast.style.display = 'flex';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 5000);
}

/**
 * Clean up on page unload
 */
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

/**
 * Handle visibility changes
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden');
    } else {
        console.log('Page visible - updating metrics');
        updateAllMetrics();
    }
});
