// ========================================
// MAIN APPLICATION CONTROLLER
// ========================================

// Global state management
const AppState = {
    mode: 'manual', // 'manual' or 'auto'
    connected: false,
    devices: {
        pump: { running: false, speed: 0 },
        feed: { running: false, intensity: 0 },
        air: { running: false, intensity: 0 },
        agitator: { running: false, speed: 0 }
    },
    metrics: {
        bubbleCount: 0,
        avgBubbleSize: 0,
        frothStability: 0,
        anomalyStatus: 'NORMAL'
    },
    piController: {
        setpoint: 120,
        kp: 0.5,
        ki: 0.05,
        output: 0,
        error: 0
    },
    system: {
        cpu: 0,
        memory: 0,
        temperature: 0,
        uptime: 0
    },
    alerts: []
};

// WebSocket connection
let ws = null;
let wsReconnectAttempts = 0;
const WS_MAX_RECONNECT = 10;
const WS_RECONNECT_DELAY = 3000;

// Initialize application on load
document.addEventListener('DOMContentLoaded', () => {
    initializeUI();
    initializeWebSocket();
    setupEventListeners();
    startClock();
    startUptimeCounter();
});

// ========================================
// WEBSOCKET CONNECTION
// ========================================

function initializeWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname || 'localhost';
    const wsPort = '8000'; // FastAPI backend port
    const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws`;

    console.log('Connecting to WebSocket:', wsUrl);
    updateConnectionStatus('connecting', 'Connecting...');

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        AppState.connected = true;
        wsReconnectAttempts = 0;
        updateConnectionStatus('connected', 'Connected');
        addAlert('success', 'WebSocket connection established');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('error', 'Connection Error');
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        AppState.connected = false;
        updateConnectionStatus('disconnected', 'Disconnected');
        
        // Attempt reconnection
        if (wsReconnectAttempts < WS_MAX_RECONNECT) {
            wsReconnectAttempts++;
            addAlert('warning', `Reconnecting... (Attempt ${wsReconnectAttempts}/${WS_MAX_RECONNECT})`);
            setTimeout(initializeWebSocket, WS_RECONNECT_DELAY);
        } else {
            addAlert('error', 'Connection lost. Please refresh the page.');
        }
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'frame':
            updateVideoFrame(data.image, data.bubbles);
            break;
        case 'metrics':
            updateMetrics(data.metrics);
            break;
        case 'anomaly':
            handleAnomaly(data);
            break;
        case 'control':
            updateControlState(data);
            break;
        case 'system':
            updateSystemHealth(data);
            break;
        case 'alert':
            addAlert(data.level, data.message);
            break;
        default:
            console.warn('Unknown message type:', data.type);
    }
}

function sendWebSocketMessage(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    } else {
        console.warn('WebSocket not connected');
        addAlert('warning', 'Cannot send command - not connected');
    }
}

// ========================================
// UI INITIALIZATION
// ========================================

function initializeUI() {
    // Set default mode display
    updateModeDisplay();
    
    // Initialize device controls
    updateDeviceUI('pump');
    updateDeviceUI('feed');
    updateDeviceUI('air');
    updateDeviceUI('agitator');
    
    // Initialize charts (imported from charts.js)
    if (typeof initializeCharts === 'function') {
        initializeCharts();
    }
}

// ========================================
// EVENT LISTENERS
// ========================================

function setupEventListeners() {
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
    // Mode switches
    document.getElementById('autoModeBtn').addEventListener('click', () => switchMode('auto'));
    document.getElementById('manualModeBtn').addEventListener('click', () => switchMode('manual'));
    
    // Emergency stop
    document.getElementById('emergencyStopBtn').addEventListener('click', handleEmergencyStop);
    
    // Device toggles
    setupDeviceToggle('pump');
    setupDeviceToggle('feed');
    setupDeviceToggle('air');
    setupDeviceToggle('agitator');
    
    // Device sliders
    setupDeviceSlider('pump', 'Speed');
    setupDeviceSlider('feed', 'Intensity');
    setupDeviceSlider('air', 'Intensity');
    setupDeviceSlider('agitator', 'Speed');
    
    // PI controller sliders
    setupPISlider('Setpoint');
    setupPISlider('Kp');
    setupPISlider('Ki');
    
    // System control buttons
    document.getElementById('startAllBtn').addEventListener('click', startAllDevices);
    document.getElementById('stopAllBtn').addEventListener('click', stopAllDevices);
    document.getElementById('calibrateBtn').addEventListener('click', handleCalibration);
    
    // Video controls
    document.getElementById('playPauseBtn').addEventListener('click', toggleVideoPlayback);
    document.getElementById('snapshotBtn').addEventListener('click', takeSnapshot);
    
    // Chart range controls
    document.querySelectorAll('[data-range]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-range]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const range = parseInt(e.target.dataset.range);
            if (typeof updateChartRange === 'function') {
                updateChartRange(range);
            }
        });
    });
    
    // Feature buttons
    document.getElementById('exportDataBtn').addEventListener('click', exportData);
    document.getElementById('settingsBtn').addEventListener('click', openSettings);
    document.getElementById('helpBtn').addEventListener('click', openHelp);
    document.getElementById('calibrationHistoryBtn').addEventListener('click', showCalibrationHistory);
    
    // Clear alerts
    document.getElementById('clearAlertsBtn').addEventListener('click', clearAlerts);
    
    // Anomaly detection toggle
    document.getElementById('anomalyToggle').addEventListener('click', toggleAnomalyDetection);
    
    // Anomaly sensitivity slider
    const anomalySensitivity = document.getElementById('anomalySensitivity');
    if (anomalySensitivity) {
        anomalySensitivity.addEventListener('input', (e) => {
            document.getElementById('anomalySensitivityValue').textContent = e.target.value;
            sendWebSocketMessage({
                type: 'control',
                action: 'set_anomaly_sensitivity',
                value: parseInt(e.target.value)
            });
        });
    }
}

// ========================================
// MODE SWITCHING
// ========================================

function switchMode(mode) {
    AppState.mode = mode;
    
    // Update UI
    document.getElementById('autoModeBtn').classList.toggle('active', mode === 'auto');
    document.getElementById('manualModeBtn').classList.toggle('active', mode === 'manual');
    
    // Show/hide control panels
    document.getElementById('manualControls').style.display = mode === 'manual' ? 'block' : 'none';
    document.getElementById('autoControls').style.display = mode === 'auto' ? 'block' : 'none';
    
    // Send mode change to backend
    sendWebSocketMessage({
        type: 'control',
        action: 'set_mode',
        mode: mode
    });
    
    addAlert('info', `Switched to ${mode.toUpperCase()} mode`);
}

function updateModeDisplay() {
    switchMode(AppState.mode);
}

// ========================================
// DEVICE CONTROL
// ========================================

function setupDeviceToggle(device) {
    const toggleBtn = document.getElementById(`${device}Toggle`);
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const isRunning = AppState.devices[device].running;
            toggleDevice(device, !isRunning);
        });
    }
}

function toggleDevice(device, running) {
    AppState.devices[device].running = running;
    
    // Update UI
    updateDeviceUI(device);
    
    // Send command to backend
    sendWebSocketMessage({
        type: 'control',
        action: 'toggle_device',
        device: device,
        running: running
    });
    
    addAlert('info', `${device.charAt(0).toUpperCase() + device.slice(1)} ${running ? 'started' : 'stopped'}`);
}

function setupDeviceSlider(device, param) {
    const slider = document.getElementById(`${device}${param}`);
    const valueDisplay = document.getElementById(`${device}${param}Value`);
    
    if (slider && valueDisplay) {
        slider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            valueDisplay.textContent = value;
            
            // Update state
            if (param === 'Speed') {
                AppState.devices[device].speed = value;
            } else if (param === 'Intensity') {
                AppState.devices[device].intensity = value;
            }
            
            // Update derived values
            updateDeviceDerivedValues(device, value);
        });
        
        slider.addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            
            // Send to backend on release
            sendWebSocketMessage({
                type: 'control',
                action: 'set_device_value',
                device: device,
                parameter: param.toLowerCase(),
                value: value
            });
        });
    }
}

function updateDeviceUI(device) {
    const toggleBtn = document.getElementById(`${device}Toggle`);
    const statusDot = toggleBtn?.querySelector('.status-dot');
    const statusText = toggleBtn?.querySelector('.status-text');
    
    const isRunning = AppState.devices[device].running;
    
    if (toggleBtn) {
        toggleBtn.classList.toggle('active', isRunning);
    }
    
    if (statusDot) {
        statusDot.classList.toggle('status-active', isRunning);
        statusDot.classList.toggle('status-stopped', !isRunning);
    }
    
    if (statusText) {
        statusText.textContent = isRunning ? 'Running' : 'Stopped';
    }
}

function updateDeviceDerivedValues(device, value) {
    switch (device) {
        case 'pump':
            // Flow rate calculation: assume 0.1 mL/min per %
            const flowRate = (value * 0.1).toFixed(1);
            document.getElementById('pumpFlowRate').textContent = `${flowRate} mL/min`;
            break;
        case 'feed':
            const feedFlow = value > 0 ? (value > 70 ? 'High' : value > 40 ? 'Medium' : 'Low') : 'Stopped';
            document.getElementById('feedFlow').textContent = feedFlow;
            break;
        case 'air':
            const airFlow = value > 0 ? (value > 70 ? 'High' : value > 40 ? 'Medium' : 'Low') : 'Stopped';
            document.getElementById('airFlow').textContent = airFlow;
            break;
        case 'agitator':
            // RPM calculation: assume max 1500 RPM at 100%
            const rpm = Math.round(value * 15);
            document.getElementById('agitatorRPM').textContent = rpm;
            break;
    }
}

// ========================================
// PI CONTROLLER
// ========================================

function setupPISlider(param) {
    const slider = document.getElementById(`pi${param}`);
    const valueDisplay = document.getElementById(`pi${param}Value`);
    
    if (slider && valueDisplay) {
        slider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            const displayValue = param === 'Setpoint' ? value : value.toFixed(2);
            valueDisplay.textContent = displayValue;
            
            AppState.piController[param.toLowerCase()] = value;
        });
        
        slider.addEventListener('change', (e) => {
            const value = parseFloat(e.target.value);
            
            sendWebSocketMessage({
                type: 'control',
                action: 'set_pi_parameter',
                parameter: param.toLowerCase(),
                value: value
            });
            
            addAlert('info', `PI ${param} updated to ${value}`);
        });
    }
}

// ========================================
// SYSTEM CONTROLS
// ========================================

function startAllDevices() {
    ['pump', 'feed', 'air', 'agitator'].forEach(device => {
        toggleDevice(device, true);
    });
    addAlert('success', 'All devices started');
}

function stopAllDevices() {
    ['pump', 'feed', 'air', 'agitator'].forEach(device => {
        toggleDevice(device, false);
    });
    addAlert('info', 'All devices stopped');
}

function handleEmergencyStop() {
    if (confirm('Are you sure you want to trigger EMERGENCY STOP? This will halt all operations immediately.')) {
        sendWebSocketMessage({
            type: 'control',
            action: 'emergency_stop'
        });
        
        // Immediately stop all devices in UI
        stopAllDevices();
        
        // Update system status
        document.getElementById('systemStatusPill').textContent = '● EMERGENCY STOP';
        document.getElementById('systemStatusPill').className = 'status-pill';
        document.getElementById('systemStatusPill').style.backgroundColor = 'rgba(231, 76, 60, 0.3)';
        document.getElementById('systemStatusPill').style.color = 'var(--accent-danger)';
        
        addAlert('error', 'EMERGENCY STOP ACTIVATED');
    }
}

function handleCalibration() {
    addAlert('info', 'Calibration routine started...');
    sendWebSocketMessage({
        type: 'control',
        action: 'calibrate'
    });
}

function toggleAnomalyDetection() {
    const toggle = document.getElementById('anomalyToggle');
    const isActive = toggle.classList.contains('active');
    
    toggle.classList.toggle('active');
    const statusDot = toggle.querySelector('.status-dot');
    const statusText = toggle.querySelector('.status-text');
    
    if (statusDot) {
        statusDot.classList.toggle('status-active');
        statusDot.classList.toggle('status-stopped');
    }
    
    if (statusText) {
        statusText.textContent = isActive ? 'Inactive' : 'Active';
    }
    
    sendWebSocketMessage({
        type: 'control',
        action: 'toggle_anomaly_detection',
        enabled: !isActive
    });
}

// ========================================
// DATA UPDATES
// ========================================

function updateMetrics(metrics) {
    AppState.metrics = { ...AppState.metrics, ...metrics };
    
    // Bubble count
    if (metrics.bubble_count !== undefined) {
        document.getElementById('bubbleCount').textContent = metrics.bubble_count;
        
        // Update trend (simplified - compare to previous)
        const trend = metrics.bubble_count_trend || 0;
        const trendIcon = trend > 0 ? '↗️' : trend < 0 ? '↘️' : '➡️';
        document.querySelector('#bubbleCountTrend .trend-icon').textContent = trendIcon;
        document.querySelector('#bubbleCountTrend .trend-value').textContent = `${Math.abs(trend)}%`;
    }
    
    // Average bubble size
    if (metrics.avg_bubble_size !== undefined) {
        document.getElementById('avgBubbleSize').textContent = metrics.avg_bubble_size.toFixed(1);
    }
    
    // Froth stability
    if (metrics.froth_stability !== undefined) {
        const stability = Math.round(metrics.froth_stability * 100);
        document.getElementById('frothStability').textContent = `${stability}%`;
        document.getElementById('stabilityFill').style.width = `${stability}%`;
    }
    
    // Update charts
    if (typeof updateChartsData === 'function') {
        updateChartsData(metrics);
    }
}

function updateControlState(data) {
    if (data.pi_output !== undefined) {
        document.getElementById('piOutput').textContent = `${Math.round(data.pi_output)}%`;
    }
    
    if (data.pi_error !== undefined) {
        document.getElementById('piError').textContent = data.pi_error.toFixed(1);
    }
    
    if (data.reagent_level !== undefined) {
        const level = Math.round(data.reagent_level);
        document.getElementById('reagentLevel').textContent = `${level}%`;
        document.getElementById('reagentProgressFill').style.width = `${level}%`;
    }
    
    if (data.total_consumption !== undefined) {
        document.getElementById('totalConsumption').textContent = `${data.total_consumption.toFixed(2)} L`;
    }
}

function handleAnomaly(data) {
    const statusEl = document.getElementById('anomalyStatus');
    const cardEl = document.getElementById('anomalyCard');
    const timeEl = document.getElementById('anomalyTime');
    
    if (data.status) {
        statusEl.textContent = data.status.toUpperCase();
        statusEl.className = 'metric-value anomaly-status';
        
        if (data.status === 'warning') {
            statusEl.classList.add('warning');
            addAlert('warning', data.message || 'Anomaly detected - Warning level');
        } else if (data.status === 'critical') {
            statusEl.classList.add('critical');
            addAlert('error', data.message || 'Anomaly detected - Critical level');
        }
    }
    
    if (timeEl) {
        timeEl.textContent = `Last check: ${new Date().toLocaleTimeString()}`;
    }
    
    // Update anomaly detection panel in auto mode
    const anomalyLastCheck = document.getElementById('anomalyLastCheck');
    if (anomalyLastCheck) {
        const icon = data.status === 'normal' ? '✅' : data.status === 'warning' ? '⚠️' : '❌';
        anomalyLastCheck.textContent = `${new Date().toLocaleTimeString()} ${icon}`;
    }
}

function updateSystemHealth(data) {
    if (data.cpu !== undefined) {
        AppState.system.cpu = data.cpu;
        const cpuPercent = Math.round(data.cpu);
        document.getElementById('cpuValue').textContent = `${cpuPercent}%`;
        document.getElementById('cpuFill').style.width = `${cpuPercent}%`;
    }
    
    if (data.memory !== undefined) {
        AppState.system.memory = data.memory;
        const memPercent = Math.round(data.memory);
        document.getElementById('memoryValue').textContent = `${memPercent}%`;
        document.getElementById('memoryFill').style.width = `${memPercent}%`;
    }
    
    if (data.temperature !== undefined) {
        AppState.system.temperature = data.temperature;
        const temp = Math.round(data.temperature);
        document.getElementById('tempValue').textContent = `${temp}°C`;
        const tempPercent = Math.min((temp / 80) * 100, 100); // Assuming 80°C max
        document.getElementById('tempFill').style.width = `${tempPercent}%`;
    }
    
    // Hardware status
    if (data.hardware_status) {
        updateHardwareStatus(data.hardware_status);
    }
}

function updateHardwareStatus(status) {
    const indicators = {
        camera: document.getElementById('cameraStatus'),
        pump: document.getElementById('pumpStatusIndicator'),
        network: document.getElementById('networkStatus'),
        storage: document.getElementById('storageStatus')
    };
    
    Object.keys(status).forEach(device => {
        const indicator = indicators[device];
        if (indicator) {
            indicator.className = 'status-indicator';
            indicator.classList.add(status[device] ? 'status-active' : 'status-error');
        }
    });
}

// ========================================
// VIDEO HANDLING
// ========================================

let videoPlaying = true;
let frameCount = 0;
let fpsStartTime = Date.now();

function updateVideoFrame(imageData, bubbles) {
    const canvas = document.getElementById('videoCanvas');
    const ctx = canvas.getContext('2d');
    
    if (!imageData) return;
    
    const img = new Image();
    img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // Draw bubble overlays if provided
        if (bubbles && bubbles.length > 0) {
            drawBubbleOverlays(ctx, bubbles);
        }
        
        // Update FPS
        frameCount++;
        const now = Date.now();
        if (now - fpsStartTime >= 1000) {
            document.getElementById('frameRate').textContent = `${frameCount} FPS`;
            frameCount = 0;
            fpsStartTime = now;
        }
        
        // Update bubble overlay count
        if (bubbles) {
            document.getElementById('bubbleOverlay').textContent = `Bubbles: ${bubbles.length}`;
        }
    };
    
    img.src = `data:image/jpeg;base64,${imageData}`;
}

function drawBubbleOverlays(ctx, bubbles) {
    ctx.strokeStyle = '#27ae60';
    ctx.lineWidth = 2;
    
    bubbles.forEach(bubble => {
        if (bubble.contour) {
            ctx.beginPath();
            bubble.contour.forEach((point, i) => {
                if (i === 0) {
                    ctx.moveTo(point.x, point.y);
                } else {
                    ctx.lineTo(point.x, point.y);
                }
            });
            ctx.closePath();
            ctx.stroke();
        }
    });
}

function toggleVideoPlayback() {
    videoPlaying = !videoPlaying;
    const btn = document.getElementById('playPauseBtn');
    btn.textContent = videoPlaying ? '⏸️' : '▶️';
    
    sendWebSocketMessage({
        type: 'control',
        action: 'video_playback',
        playing: videoPlaying
    });
}

function takeSnapshot() {
    const canvas = document.getElementById('videoCanvas');
    const dataURL = canvas.toDataURL('image/png');
    
    // Create download link
    const link = document.createElement('a');
    link.download = `flotation_snapshot_${Date.now()}.png`;
    link.href = dataURL;
    link.click();
    
    addAlert('success', 'Snapshot saved');
}

// ========================================
// ALERTS MANAGEMENT
// ======================================== 

function addAlert(level, message) {
    const timestamp = new Date().toLocaleTimeString();
    const alert = {
        timestamp,
        level,
        message
    };
    
    AppState.alerts.unshift(alert);
    
    // Update UI
    const alertsList = document.getElementById('alertsList');
    const alertItem = document.createElement('div');
    alertItem.className = `alert-item alert-${level}`;
    alertItem.innerHTML = `
        <span class="alert-timestamp">${timestamp}</span>
        <span class="alert-message">${message}</span>
    `;
    
    alertsList.insertBefore(alertItem, alertsList.firstChild);
    
    // Update counter
    updateAlertCounter();
    
    // Limit to 50 alerts
    if (AppState.alerts.length > 50) {
        AppState.alerts = AppState.alerts.slice(0, 50);
        const items = alertsList.querySelectorAll('.alert-item');
        if (items.length > 50) {
            items[items.length - 1].remove();
        }
    }
}

function clearAlerts() {
    AppState.alerts = [];
    document.getElementById('alertsList').innerHTML = `
        <div class="alert-item alert-info">
            <span class="alert-timestamp">--:--:--</span>
            <span class="alert-message">No alerts</span>
        </div>
    `;
    updateAlertCounter();
}

function updateAlertCounter() {
    const count = AppState.alerts.length;
    document.getElementById('alertCount').textContent = count;
}

// ========================================
// CONNECTION STATUS
// ========================================

function updateConnectionStatus(status, text) {
    const statusEl = document.getElementById('connectionStatus');
    const statusDot = statusEl.querySelector('.status-dot');
    const statusText = document.getElementById('statusText');
    
    statusDot.className = 'status-dot';
    
    switch (status) {
        case 'connected':
            statusDot.classList.add('status-active');
            break;
        case 'connecting':
            statusDot.classList.add('status-connecting');
            break;
        case 'error':
        case 'disconnected':
            statusDot.classList.add('status-error');
            break;
    }
    
    statusText.textContent = text;
}

// ========================================
// THEME TOGGLE
// ========================================

function toggleTheme() {
    const body = document.body;
    const themeBtn = document.getElementById('themeToggle');
    
    body.classList.toggle('light-theme');
    const isLight = body.classList.contains('light-theme');
    
    themeBtn.textContent = isLight ? '☀️' : '🌙';
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

// Load saved theme
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
    document.body.classList.add('light-theme');
    document.getElementById('themeToggle').textContent = '☀️';
}

// ========================================
// UTILITIES
// ========================================

function startClock() {
    function updateClock() {
        const now = new Date();
        const dateStr = now.toLocaleDateString('en-US', { 
            weekday: 'short', 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
        document.getElementById('datetime').textContent = `${dateStr} ${timeStr}`;
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

function startUptimeCounter() {
    const startTime = Date.now();
    
    function updateUptime() {
        const elapsed = Date.now() - startTime;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        
        document.getElementById('uptime').textContent = 
            `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    
    setInterval(updateUptime, 1000);
}

function exportData() {
    addAlert('info', 'Exporting data...');
    
    sendWebSocketMessage({
        type: 'control',
        action: 'export_data',
        range: 'last_24h'
    });
    
    // Simulate export (in production, this would download from backend)
    setTimeout(() => {
        addAlert('success', 'Data export complete');
    }, 2000);
}

function openSettings() {
    addAlert('info', 'Settings panel coming soon');
}

function openHelp() {
    window.open('https://github.com/yourusername/flotation-project/wiki', '_blank');
}

function showCalibrationHistory() {
    addAlert('info', 'Calibration history coming soon');
}

// ========================================
// ERROR HANDLING
// ========================================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    addAlert('error', `Error: ${event.error.message}`);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    addAlert('error', `Promise error: ${event.reason}`);
});

console.log('Dashboard application initialized');
