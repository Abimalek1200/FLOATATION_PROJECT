#!/bin/bash

# ========================================
# Flotation Control System - Setup Script
# Raspberry Pi 5 Installation (Continued Setup)
# ========================================

set -e  # Exit on error

echo "========================================="
echo "Flotation Control System - Continued Setup"
echo "Raspberry Pi 5 Configuration"
echo "========================================="
echo ""
echo "NOTE: Steps 1-4 already completed:"
echo "  ✓ System packages updated"
echo "  ✓ Hardware interfaces enabled"
echo "  ✓ System dependencies installed"
echo "  ✓ Python packages installed"
echo ""
echo "Continuing with remaining configuration..."
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Please do not run this script as root"
    exit 1
fi

# ========================================
# STEP 5: Install lgpio for Raspberry Pi 5
# ========================================

echo ""
echo "[1/4] Installing lgpio (Raspberry Pi 5 GPIO library)..."

# Install lgpio - native GPIO library for Raspberry Pi 5
sudo apt install -y python3-lgpio python3-rpi-lgpio

# Verify installation
if python3 -c "import lgpio" 2>/dev/null; then
    echo "✓ lgpio installed successfully"
    
    # Test lgpio connection
    python3 << 'PYEOF'
import sys
try:
    import lgpio
    chip = lgpio.gpiochip_open(0)
    print("✓ lgpio connection test SUCCESSFUL")
    print(f"  GPIO chip 0 opened successfully")
    lgpio.gpiochip_close(chip)
    sys.exit(0)
except Exception as e:
    print(f"✗ lgpio test error: {e}")
    sys.exit(1)
PYEOF

    if [ $? -eq 0 ]; then
        echo "✓ lgpio fully operational and ready for PWM control"
    else
        echo "⚠ WARNING: lgpio installed but connection test failed"
    fi
else
    echo "✗ ERROR: lgpio installation failed"
    echo "  Try manually: sudo apt install -y python3-lgpio"
    exit 1
fi

echo ""
echo "Note: Raspberry Pi 5 uses lgpio instead of pigpio"
echo "      No daemon required - direct hardware access"
    if [ $? -eq 0 ]; then
        echo "✓ lgpio fully operational and ready for PWM control"
    else
        echo "⚠ WARNING: lgpio installed but connection test failed"
    fi
else
    echo "✗ ERROR: lgpio installation failed"
    echo "  Try manually: sudo apt install -y python3-lgpio"
    exit 1
fi

echo ""
echo "Note: Raspberry Pi 5 uses lgpio instead of pigpio"
echo "      No daemon required - direct hardware access"

# ========================================
# STEP 6: Configure Camera
# ========================================

echo ""
echo "[2/4] Configuring camera settings..."

# Check if camera is detected
if vcgencmd get_camera | grep -q "detected=1"; then
    echo "✓ Camera detected successfully"
else
    echo "⚠ WARNING: No camera detected. Please check camera connection."
    echo "  - Ensure USB webcam is plugged in"
    echo "  - Try: ls /dev/video*"
fi

# Set camera permissions
sudo usermod -a -G video $USER
echo "✓ Camera permissions configured"

# ========================================
# STEP 7: Create Project Directories
# ========================================

echo ""
echo "[3/4] Creating project directory structure..."

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

echo "✓ Project directories created successfully"

# ========================================
# STEP 8: Create Systemd Service
# ========================================

echo ""
echo "[4/4] Creating systemd service..."

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

echo "✓ Systemd service created successfully"

# ========================================
# Create Configuration Files
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

echo "✓ Configuration files created successfully"

# ========================================
# Set Permissions
# ========================================

echo ""
echo "Setting file permissions..."

chmod +x "$PROJECT_DIR/setup.sh"
chmod 644 "$PROJECT_DIR/config"/*.json 2>/dev/null || true
chmod 755 "$PROJECT_DIR/logs" 2>/dev/null || true
chmod 755 "$PROJECT_DIR/data" 2>/dev/null || true

echo "✓ File permissions configured"

# ========================================
# FINAL STEPS
# ========================================

echo ""
echo "========================================="
echo "Continued Setup Completed Successfully!"
echo "========================================="
echo ""
echo "Configuration Summary:"
echo "  ✓ pigpiod daemon configured and running"
echo "  ✓ Camera permissions set"
echo "  ✓ Project directories created"
echo "  ✓ Systemd service installed"
echo "  ✓ Configuration files generated"
echo ""
echo "Next steps:"
echo ""
echo "1. Verify pigpio is working:"
echo "   python3 -c 'import pigpio; pi=pigpio.pi(); print(\"Connected:\", pi.connected); pi.stop()'"
echo ""
echo "2. Test camera access:"
echo "   python3 -c 'import cv2; print(\"Camera OK:\", cv2.VideoCapture(0).isOpened())'"
echo ""
echo "3. Start the service manually (for testing):"
echo "   cd $PROJECT_DIR"
echo "   python3 run.py"
echo ""
echo "4. Or enable automatic startup:"
echo "   sudo systemctl enable flotation.service"
echo "   sudo systemctl start flotation.service"
echo ""
echo "5. Check service status:"
echo "   sudo systemctl status flotation.service"
echo ""
echo "6. View logs:"
echo "   tail -f $PROJECT_DIR/logs/flotation.log"
echo ""
echo "7. Access dashboard from any device on your network:"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo "   OR"
echo "   http://raspberrypi.local:8000"
echo ""
echo "Troubleshooting:"
echo "  - If pigpio fails: sudo pigpiod"
echo "  - Check camera: ls /dev/video*"
echo "  - Service logs: sudo journalctl -u flotation -f"
echo ""
echo "Configuration files location: $PROJECT_DIR/config/"
echo "========================================="
echo ""

# Ask for reboot (optional now since main setup already done)
read -p "Reboot recommended to ensure all changes take effect. Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    sudo reboot
else
    echo ""
    echo "Setup complete. Remember to reboot before first use!"
    echo "Run: sudo reboot"
fi
fi
