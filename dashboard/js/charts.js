// ========================================
// CHART CONFIGURATIONS & DATA MANAGEMENT
// ========================================

// Chart instances
let bubbleTrendChart = null;
let bubbleSizeChart = null;
let pumpActivityChart = null;
let distributionChart = null;

// Chart data storage (circular buffers)
const CHART_MAX_POINTS = 60; // 60 data points for time series
let chartTimeRange = 60; // minutes

const chartData = {
    bubbleTrend: {
        timestamps: [],
        bubbleCount: [],
        setpoint: []
    },
    bubbleSize: {
        timestamps: [],
        avgSize: [],
        sizeStdDev: []
    },
    pumpActivity: {
        timestamps: [],
        pumpDuty: [],
        reagentConsumption: []
    },
    distribution: {
        labels: ['0-50', '50-100', '100-200', '200-500', '500-1000', '1000+'],
        data: [0, 0, 0, 0, 0, 0]
    }
};

// Chart color scheme
const chartColors = {
    primary: '#2d9cdb',
    success: '#27ae60',
    warning: '#f39c12',
    danger: '#e74c3c',
    info: '#3498db',
    secondary: '#95a5a6',
    grid: 'rgba(255, 255, 255, 0.1)',
    text: '#e4e6eb'
};

// ========================================
// CHART INITIALIZATION
// ========================================

function initializeCharts() {
    initBubbleTrendChart();
    initBubbleSizeChart();
    initPumpActivityChart();
    initDistributionChart();
    
    console.log('All charts initialized');
}

// Bubble Count Trend Chart
function initBubbleTrendChart() {
    const ctx = document.getElementById('bubbleTrendChart');
    if (!ctx) return;

    bubbleTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.bubbleTrend.timestamps,
            datasets: [
                {
                    label: 'Bubble Count',
                    data: chartData.bubbleTrend.bubbleCount,
                    borderColor: chartColors.primary,
                    backgroundColor: `${chartColors.primary}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5
                },
                {
                    label: 'Setpoint',
                    data: chartData.bubbleTrend.setpoint,
                    borderColor: chartColors.warning,
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: chartColors.text,
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text,
                        maxTicksLimit: 8
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text
                    },
                    beginAtZero: true
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Bubble Size Over Time Chart
function initBubbleSizeChart() {
    const ctx = document.getElementById('bubbleSizeChart');
    if (!ctx) return;

    bubbleSizeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.bubbleSize.timestamps,
            datasets: [
                {
                    label: 'Avg. Size (px²)',
                    data: chartData.bubbleSize.avgSize,
                    borderColor: chartColors.success,
                    backgroundColor: `${chartColors.success}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    yAxisID: 'y'
                },
                {
                    label: 'Std Deviation',
                    data: chartData.bubbleSize.sizeStdDev,
                    borderColor: chartColors.info,
                    backgroundColor: `${chartColors.info}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: chartColors.text,
                        font: { size: 11 }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text,
                        maxTicksLimit: 8
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text
                    },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        color: chartColors.text
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

// Pump Activity & Reagent Consumption Chart
function initPumpActivityChart() {
    const ctx = document.getElementById('pumpActivityChart');
    if (!ctx) return;

    pumpActivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.pumpActivity.timestamps,
            datasets: [
                {
                    label: 'Pump Duty Cycle (%)',
                    data: chartData.pumpActivity.pumpDuty,
                    borderColor: chartColors.warning,
                    backgroundColor: `${chartColors.warning}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    yAxisID: 'y'
                },
                {
                    label: 'Reagent Consumed (mL)',
                    data: chartData.pumpActivity.reagentConsumption,
                    borderColor: chartColors.danger,
                    backgroundColor: `${chartColors.danger}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: chartColors.text,
                        font: { size: 11 }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text,
                        maxTicksLimit: 8
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text
                    },
                    beginAtZero: true,
                    max: 100
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        color: chartColors.text
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

// Bubble Size Distribution Histogram
function initDistributionChart() {
    const ctx = document.getElementById('distributionChart');
    if (!ctx) return;

    distributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.distribution.labels,
            datasets: [{
                label: 'Bubble Count by Size (px²)',
                data: chartData.distribution.data,
                backgroundColor: [
                    `${chartColors.primary}cc`,
                    `${chartColors.success}cc`,
                    `${chartColors.info}cc`,
                    `${chartColors.warning}cc`,
                    `${chartColors.danger}cc`,
                    `${chartColors.secondary}cc`
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((context.parsed.y / total) * 100).toFixed(1) : 0;
                            return `${context.parsed.y} bubbles (${percentage}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: chartColors.text
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text
                    },
                    beginAtZero: true
                }
            }
        }
    });
}

// ========================================
// DATA UPDATE FUNCTIONS
// ========================================

function updateChartsData(metrics) {
    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
    
    // Update bubble trend
    if (metrics.bubble_count !== undefined) {
        addDataPoint(chartData.bubbleTrend.timestamps, timestamp);
        addDataPoint(chartData.bubbleTrend.bubbleCount, metrics.bubble_count);
        addDataPoint(chartData.bubbleTrend.setpoint, metrics.setpoint || 120);
        
        if (bubbleTrendChart) {
            bubbleTrendChart.update('none'); // Update without animation for performance
        }
    }
    
    // Update bubble size
    if (metrics.avg_bubble_size !== undefined) {
        addDataPoint(chartData.bubbleSize.timestamps, timestamp);
        addDataPoint(chartData.bubbleSize.avgSize, metrics.avg_bubble_size);
        addDataPoint(chartData.bubbleSize.sizeStdDev, metrics.size_std_dev || 0);
        
        if (bubbleSizeChart) {
            bubbleSizeChart.update('none');
        }
    }
    
    // Update pump activity
    if (metrics.pump_duty_cycle !== undefined) {
        addDataPoint(chartData.pumpActivity.timestamps, timestamp);
        addDataPoint(chartData.pumpActivity.pumpDuty, metrics.pump_duty_cycle);
        
        // Calculate cumulative reagent consumption
        const flowRate = metrics.pump_duty_cycle * 0.1; // mL/min
        const lastConsumption = chartData.pumpActivity.reagentConsumption.length > 0 
            ? chartData.pumpActivity.reagentConsumption[chartData.pumpActivity.reagentConsumption.length - 1] 
            : 0;
        const newConsumption = lastConsumption + (flowRate / 60); // Per second
        
        addDataPoint(chartData.pumpActivity.reagentConsumption, newConsumption);
        
        if (pumpActivityChart) {
            pumpActivityChart.update('none');
        }
    }
    
    // Update distribution
    if (metrics.bubble_size_distribution) {
        chartData.distribution.data = metrics.bubble_size_distribution;
        if (distributionChart) {
            distributionChart.update('none');
        }
    }
}

function addDataPoint(array, value) {
    array.push(value);
    
    // Maintain circular buffer - remove oldest if exceeds max
    if (array.length > CHART_MAX_POINTS) {
        array.shift();
    }
}

// ========================================
// CHART CONTROLS
// ========================================

function updateChartRange(minutes) {
    chartTimeRange = minutes;
    
    // Calculate how many points to keep based on update frequency
    // Assuming 1 update per second, 60 points = 1 minute
    const maxPoints = minutes;
    
    // Trim data arrays if needed
    Object.keys(chartData).forEach(chartKey => {
        if (chartKey !== 'distribution') {
            Object.keys(chartData[chartKey]).forEach(dataKey => {
                const array = chartData[chartKey][dataKey];
                if (array.length > maxPoints) {
                    chartData[chartKey][dataKey] = array.slice(-maxPoints);
                }
            });
        }
    });
    
    // Update all charts
    [bubbleTrendChart, bubbleSizeChart, pumpActivityChart].forEach(chart => {
        if (chart) {
            chart.update();
        }
    });
    
    console.log(`Chart range updated to ${minutes} minutes`);
}

// ========================================
// EXPORT FUNCTIONS
// ========================================

window.initializeCharts = initializeCharts;
window.updateChartsData = updateChartsData;
window.updateChartRange = updateChartRange;

// ========================================
// THEME SUPPORT
// ========================================

function updateChartTheme(isDark) {
    const textColor = isDark ? '#e4e6eb' : '#2c3e50';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    [bubbleTrendChart, bubbleSizeChart, pumpActivityChart, distributionChart].forEach(chart => {
        if (chart) {
            // Update scales colors
            chart.options.scales.x.grid.color = gridColor;
            chart.options.scales.x.ticks.color = textColor;
            
            if (chart.options.scales.y) {
                chart.options.scales.y.grid.color = gridColor;
                chart.options.scales.y.ticks.color = textColor;
            }
            
            if (chart.options.scales.y1) {
                chart.options.scales.y1.ticks.color = textColor;
            }
            
            // Update legend
            if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = textColor;
            }
            
            chart.update();
        }
    });
}

// Listen for theme changes
const themeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
            const isDark = !document.body.classList.contains('light-theme');
            updateChartTheme(isDark);
        }
    });
});

// Observe body class changes
if (document.body) {
    themeObserver.observe(document.body, { attributes: true });
}

console.log('Charts module loaded');
