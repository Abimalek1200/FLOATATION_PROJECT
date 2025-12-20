#!/bin/bash

# ========================================
# Flotation Control System - Setup Script
# Raspberry Pi 5 Installation
# ========================================

set -e  # Exit on error

echo "========================================="
echo "Flotation Control System Setup"
echo "Raspberry Pi 5 Configuration"
echo "========================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Please do not run this script as root"
    exit 1
fi

# ========================================
# STEP 1: System Update
# ========================================

echo ""
echo "[1/8] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# ========================================
# STEP 2: Enable Hardware Interfaces
# ========================================

echo ""
echo "[2/8] Enabling hardware interfaces (Camera, I2C, SPI)..."

# Enable camera interface
sudo raspi-config nonint do_camera 0

# Enable I2C (if using I2C sensors)
sudo raspi-config nonint do_i2c 0

# Enable SPI (if using SPI devices)
sudo raspi-config nonint do_spi 0

echo "Hardware interfaces enabled successfully"

# ========================================
# STEP 3: Install System Dependencies
# ========================================

echo ""
echo "[3/8] Installing system dependencies..."

sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    python3-pigpio \
    libopenblas-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
ny    libhdf5-dev \
    libhdf5-serial-dev \
    libharfbuzz-dev \
    libwebp-dev \
    git \
    cmake \
    build-essential \
    pkg-config

echo "System dependencies installed successfully"

# ========================================
# STEP 4: Install Python Dependencies
# ========================================

echo ""
echo "[4/8] Installing Python packages..."

# Upgrade pip
python3 -m pip install --upgrade pip --break-system-packages

# Install required Python packages from apt (system packages are more compatible)
sudo apt install -y \
    python3-fastapi \
    python3-uvicorn \
    python3-websockets \
    python3-pil \
    python3-dotenv

# Install remaining packages via pip with --break-system-packages
pip3 install --break-system-packages \
    opencv-python \
    scikit-learn \
    python-multipart \
    aiofiles

echo "Python packages installed successfully"

# ========================================
# STEP 5: Setup pigpio Daemon
# ========================================

echo ""
echo "[5/8] Configuring pigpio daemon for PWM control..."

# Enable and start pigpio daemon
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Verify pigpio is running
if systemctl is-active --quiet pigpiod; then
    echo "pigpio daemon started successfully"
else
    echo "WARNING: pigpio daemon failed to start"
fi

# ========================================
# STEP 6: Configure Camera
# ========================================

echo ""
echo "[6/8] Configuring camera settings..."

# Check if camera is detected
if vcgencmd get_camera | grep -q "detected=1"; then
    echo "Camera detected successfully"
else
    echo "WARNING: No camera detected. Please check camera connection."
fi

# Set camera permissions
sudo usermod -a -G video $USER

# ========================================
# STEP 7: Create Project Directories
# ========================================

echo ""
echo "[7/8] Creating project directory structure..."

# Get the directory where the script is located
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create necessary directories
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/snapshots"
mkdir -p "$PROJECT_DIR/config"
mkdir -p "$PROJECT_DIR/src/vision"
mkdir -p "$PROJECT_DIR/src/control"
mkdir -p "$PROJECT_DIR/src/ml"
mkdir -p "$PROJECT_DIR/src/api"
mkdir -p "$PROJECT_DIR/src/utils"

echo "Project directories created successfully"

# ========================================
# STEP 8: Create Systemd Service
# ========================================

echo ""
echo "[8/8] Creating systemd service..."

# Create service file
sudo tee /etc/systemd/system/flotation.service > /dev/null <<EOF
[Unit]
Description=Flotation Control System
After=network.target pigpiod.service
Requires=pigpiod.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 $PROJECT_DIR/run.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/flotation.log
StandardError=append:$PROJECT_DIR/logs/flotation-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

echo "Systemd service created successfully"

# ========================================
# STEP 9: Create Configuration Files
# ========================================

echo ""
echo "Creating default configuration files..."

# Camera configuration
cat > "$PROJECT_DIR/config/camera_config.json" <<EOF
{
    "device_id": 0,
    "width": 640,
    "height": 480,
    "fps": 15,
    "auto_exposure": false,
    "exposure": 100,
    "brightness": 50,
    "contrast": 50,
    "saturation": 50,
    "led_ring_usb": true,
    "led_ring_note": "USB-powered LED ring light (always on when connected)"
}
EOF

# Control configuration
cat > "$PROJECT_DIR/config/control_config.json" <<EOF
{
    "pi_controller": {
        "kp": 0.5,
        "ki": 0.05,
        "setpoint": 120,
        "output_limits": [0, 80],
        "integral_limits": [-50, 50]
    },
    "frother_pump": {
        "pin": 12,
        "frequency_hz": 1000,
        "calibration_ml_per_pwm": 0.1,
        "max_duty_cycle": 80,
        "description": "Peristaltic pump for frother reagent dosing"
    },
    "feed_pump": {
        "pin": 15,
        "frequency_hz": 1000,
        "description": "Feed pump for slurry input"
    },
    "air_pump": {
        "pin": 14,
        "frequency_hz": 1000,
        "description": "Air pump for bubble generation"
    },
    "agitator": {
        "pin": 13,
        "frequency_hz": 1000,
        "max_rpm": 1500,
        "description": "Agitator motor for cell mixing"
    },
    "estop_pin": 22,
    "watchdog_timeout_seconds": 5,
    "gpio_notes": "LED ring light is USB-powered, not GPIO-controlled. All pumps use hardware PWM pins."
}
EOF

# System configuration
cat > "$PROJECT_DIR/config/system_config.json" <<EOF
{
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "cors_origins": ["*"],
        "allow_credentials": true,
        "network_access": "Accessible from any device on local network"
    },
    "database": {
        "path": "data/flotation.db",
        "retention_days": 7
    },
    "logging": {
        "level": "INFO",
        "file": "logs/flotation.log",
        "max_bytes": 10485760,
        "backup_count": 5
    },
    "vision": {
        "processing_interval_ms": 1000,
        "min_bubble_area": 50,
        "max_bubble_area": 5000,
        "threshold_method": "adaptive",
        "frame_skip_on_high_cpu": true,
        "cpu_threshold": 80
    },
    "anomaly_detection": {
        "enabled": true,
        "contamination": 0.1,
        "n_estimators": 50,
        "max_samples": 256,
        "model_path": "data/anomaly_model.pkl"
    }
}
EOF

echo "Configuration files created successfully"

# ========================================
# STEP 10: Set Permissions
# ========================================

echo ""
echo "Setting file permissions..."

chmod +x "$PROJECT_DIR/setup.sh"
chmod 644 "$PROJECT_DIR/config"/*.json
chmod 755 "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/data"

# ========================================
# FINAL STEPS
# ========================================

echo ""
echo "========================================="
echo "Setup completed successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Reboot your Raspberry Pi to apply changes:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify hardware:"
echo "   vcgencmd get_camera    # Check camera"
echo "   sudo systemctl status pigpiod    # Check pigpio"
echo ""
echo "3. Test camera access:"
echo "   python3 -c 'import cv2; print(cv2.VideoCapture(0).isOpened())'"
echo ""
echo "4. Start the service manually (for testing):"
echo "   python3 run.py"
echo ""
echo "5. Or enable automatic startup:"
echo "   sudo systemctl enable flotation.service"
echo "   sudo systemctl start flotation.service"
echo ""
echo "6. Check service status:"
echo "   sudo systemctl status flotation.service"
echo ""
echo "7. View logs:"
echo "   tail -f logs/flotation.log"
echo ""
echo "8. Access dashboard from any device on your network:"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo "   OR"
echo "   http://raspberrypi.local:8000"
echo ""
echo "   Note: Dashboard is accessible from:"
echo "   - Laptops, tablets, phones on same WiFi"
echo "   - Any device on the same local network"
echo "   - Save this IP for easy access!"
echo ""
echo "Configuration files created in: $PROJECT_DIR/config/"
echo "========================================="

# Ask for reboot
read -p "Would you like to reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    sudo reboot
fi
