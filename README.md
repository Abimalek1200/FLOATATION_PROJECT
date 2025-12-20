# Flotation Control System - README

## Project Overview

Automated reagent dosing control system for small-to-medium scale gold flotation operations. This Raspberry Pi 5-based system uses real-time computer vision to monitor froth characteristics and automatically adjust frother dosage using a closed-loop PI controller with anomaly detection.

## Hardware Requirements

### Raspberry Pi Setup
- **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- **MicroSD Card**: 32GB minimum (64GB recommended)
- **Power Supply**: Official Raspberry Pi 5 27W USB-C power supply
- **Cooling**: Active cooling fan or heatsink (system runs continuously)
- **USB Ports**: 2 USB ports required (webcam + LED ring light)

### Camera System
- **USB Webcam**: 1080p resolution, minimum 15 FPS
- **LED Ring Light**: USB-powered (always on when connected, no GPIO control needed)
- **Camera Mount**: Positioned above flotation cell
- **USB Hub**: Recommended for connecting both webcam and LED ring light

### Flotation Equipment
- **Acrylic Flotation Cell**: Transparent for camera viewing
- **Peristaltic Pump**: For reagent dosing (PWM controlled via GPIO)
- **Agitator Motor**: Variable speed (PWM controlled)
- **Air Pump**: For bubble generation (PWM controlled)
- **Feed Pump**: For slurry input (PWM controlled)

### Safety Equipment
- **Emergency Stop Button**: Hard-wired to GPIO (always functional)
- **Voltage Protection**: Proper isolation for GPIO pins

### Optional Equipment
- **Ethernet Cable**: For stable network connection
- **UPS/Battery Backup**: For power reliability
- **Monitor/Keyboard/Mouse**: For initial setup only

## Software Prerequisites

### Operating System
- **Raspberry Pi OS** (64-bit, Bookworm or later)
- Lite version acceptable, Desktop version recommended for initial setup

### Python Version
- **Python 3.11+** (comes pre-installed on Raspberry Pi OS)

### System Libraries
Automatically installed by `setup.sh`:
- OpenCV dependencies
- pigpio daemon
- NumPy/SciPy libraries
- FastAPI/Uvicorn

## Installation Guide

### Step 1: Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Flash Raspberry Pi OS (64-bit) to microSD card
3. Configure WiFi/SSH during imaging (optional)
4. Insert SD card and boot Raspberry Pi

### Step 2: Initial System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install git
sudo apt install git -y

# Clone project repository
cd ~
git clone https://github.com/yourusername/flotation-project.git
cd flotation-project
```

### Step 3: Run Setup Script

```bash
# Make setup script executable
chmod +x setup.sh

# Run automated setup
./setup.sh
```

The setup script will:
- ✅ Update system packages
- ✅ Enable camera, I2C, SPI interfaces
- ✅ Install system dependencies (OpenCV, pigpio, etc.)
- ✅ Install Python packages from requirements.txt
- ✅ Configure pigpio daemon for PWM control
- ✅ Create project directory structure
- ✅ Generate default configuration files
- ✅ Create systemd service for auto-start
- ✅ Set proper file permissions

### Step 4: Configure Static IP (Recommended)

For reliable access, set a static IP address:

```bash
# Find current IP and network info
ip addr show

# Edit dhcpcd configuration
sudo nano /etc/dhcpcd.conf

# Add these lines at the end (adjust to your network):
# interface wlan0  # Use eth0 for Ethernet
# static ip_address=192.168.1.100/24
# static routers=192.168.1.1
# static domain_name_servers=192.168.1.1 8.8.8.8

# Save (Ctrl+O, Enter, Ctrl+X)
```

### Step 5: Reboot

```bash
sudo reboot
```

### Step 5: Verify Installation

After reboot:

```bash
# Check camera detection
vcgencmd get_camera

# Verify pigpio daemon
sudo systemctl status pigpiod

# Test Python imports
python3 -c "import cv2, numpy, sklearn, fastapi; print('All imports successful')"

# Test camera access
python3 -c "import cv2; print('Camera OK' if cv2.VideoCapture(0).isOpened() else 'Camera FAIL')"
```

## Hardware Wiring Guide

### GPIO Pin Assignments (BCM Numbering)

| Device | GPIO Pin | Function | Notes |
|--------|----------|----------|-------|
| **Frother Pump (Peristaltic)** | **GPIO 12** | **PWM Output** | **Hardware PWM (PWM0)** |
| **Agitator Motor** | **GPIO 13** | **PWM Output** | **Hardware PWM (PWM1)** |
| **Air Pump** | **GPIO 14** | **PWM Output** | **Software PWM** |
| **Feed Pump** | **GPIO 15** | **PWM Output** | **Software PWM** |
| Emergency Stop | GPIO 22 | Input (Pull-up) | Active LOW |
| **LED Ring Light** | **USB Port** | **Power Only** | **USB-powered (always on)** |

### Wiring Safety
⚠️ **IMPORTANT**: 
- Use proper level shifters for 5V devices
- Never connect motors directly to GPIO pins
- Use relay modules or motor drivers (L298N, TB6612)
- Ensure common ground between Pi and external circuits
- Add flyback diodes to all motor connections
- **LED ring light**: USB-powered only, DO NOT connect to GPIO

### Emergency Stop Wiring
```
GPIO 22 ----[10kΩ]---- 3.3V
            |
         [E-STOP]
            |
           GND
```

## Configuration

### Camera Settings (`config/camera_config.json`)

```json
{
    "device_id": 0,
    "width": 640,
    "height": 480,
    "fps": 15,
    "exposure": 100,
    "brightness": 50
}
```

### Control Parameters (`config/control_config.json`)

```json
{
    "pi_controller": {
        "kp": 0.5,
        "ki": 0.05,
        "setpoint": 120
    },
    "pump": {
        "pin": 18,
        "max_duty_cycle": 80
    }
}
```

### System Settings (`config/system_config.json`)

```json
{
    "api": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "logging": {
        "level": "INFO"
    }
}
```

## Running the Application

### Manual Start (Testing)

```bash
cd ~/flotation-project
python3 run.py
```

### Enable Auto-Start

```bash
# Enable service
sudo systemctl enable flotation.service

# Start service
sudo systemctl start flotation.service

# Check status
sudo systemctl status flotation.service
```

### View Logs

```bash
# Real-time logs
tail -f logs/flotation.log

# Error logs
tail -f logs/flotation-error.log

# System logs
journalctl -u flotation.service -f
```

## Accessing the Dashboard

The dashboard is **accessible from any device on the same network** as the Raspberry Pi.

### Option 1: Using Hostname (Recommended)
```
http://raspberrypi.local:8000
```
*Works on most devices if mDNS/Bonjour is enabled*

### Option 2: Using IP Address (Most Reliable)
```
http://<raspberry-pi-ip-address>:8000
```

### Find Raspberry Pi IP Address:

**On Raspberry Pi:**
```bash
hostname -I
# Example output: 192.168.1.100
```

**On Windows PC (same network):**
```powershell
ping raspberrypi.local
# Or scan network:
arp -a | findstr "b8-27-eb"  # RPi MAC addresses start with b8:27:eb or dc:a6:32
```

**On Android/iOS:**
- Use apps like "Network Scanner" or "Fing"
- Look for device named "raspberrypi"

### Example Access from Different Devices:

| Device | Access URL |
|--------|------------|
| Laptop on WiFi | `http://192.168.1.100:8000` |
| Tablet | `http://raspberrypi.local:8000` |
| Phone | `http://192.168.1.100:8000` |
| Desktop PC | `http://raspberrypi.local:8000` |

### Network Requirements:
- ✅ All devices must be on the **same local network** (WiFi or LAN)
- ✅ Raspberry Pi must have a **static or reserved IP** (recommended)
- ✅ Firewall on Pi must allow port 8000 (automatic with setup.sh)
- ⚠️ NOT accessible from outside your local network (for security)

## Performance Optimization

### Recommended Settings

**For Raspberry Pi 5 (4GB RAM)**:
- Video resolution: 640x480
- Frame rate: 10-15 FPS
- Chart update interval: 1 second
- Database retention: 7 days

**For Raspberry Pi 5 (8GB RAM)**:
- Video resolution: 1280x720
- Frame rate: 15-20 FPS
- Chart update interval: 0.5 seconds
- Database retention: 14 days

### CPU Governor (Optional)
```bash
# Set performance mode
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Disable GUI (Headless Operation)
```bash
# Boot to CLI only
sudo raspi-config nonint do_boot_behaviour B1
```

## Troubleshooting

### Camera Not Detected
```bash
# List USB devices
lsusb

# Check video devices
ls -l /dev/video*

# Test camera with v4l2
v4l2-ctl --list-devices

# If using legacy camera interface
vcgencmd get_camera
sudo raspi-config nonint do_camera 0
sudo reboot
```

### LED Ring Light Not Working
```bash
# Check USB devices
lsusb | grep -i light

# Check USB power
vcgencmd get_throttled

# If ring light is dimmable via USB
# No software control needed - it's powered directly
```

### pigpio Daemon Not Running
```bash
# Start daemon manually
sudo systemctl start pigpiod

# Check status
sudo systemctl status pigpiod

# Enable auto-start
sudo systemctl enable pigpiod
```

### High CPU Usage
- Reduce video resolution in `config/camera_config.json`
- Lower frame rate to 10 FPS
- Enable frame skipping in `config/system_config.json`

### WebSocket Connection Failed
```bash
# Check if service is running
sudo systemctl status flotation.service

# Check firewall
sudo ufw status

# Allow port 8000
sudo ufw allow 8000
```

### GPIO Permission Denied
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER
sudo reboot
```

### Cannot Access Dashboard from Other Devices

**Check if service is running:**
```bash
sudo systemctl status flotation.service
```

**Verify Pi is listening on all interfaces:**
```bash
sudo netstat -tulpn | grep :8000
# Should show: 0.0.0.0:8000 (not 127.0.0.1:8000)
```

**Test from Raspberry Pi first:**
```bash
curl http://localhost:8000
# Should return HTML
```

**Check firewall (if enabled):**
```bash
# Allow port 8000
sudo ufw allow 8000/tcp
sudo ufw status
```

**Find Pi's IP address:**
```bash
hostname -I
ifconfig
ip addr show
```

**Test connectivity from another device:**
```bash
# On Windows:
ping 192.168.1.100
telnet 192.168.1.100 8000

# On Linux/Mac:
ping 192.168.1.100
telnet 192.168.1.100 8000
```

**Common Issues:**
- ❌ Wrong IP address → Use `hostname -I` on Pi
- ❌ Different network/WiFi → Ensure same network
- ❌ VPN enabled → Disable VPN on accessing device
- ❌ Service not running → `sudo systemctl start flotation.service`
- ❌ Firewall blocking → `sudo ufw allow 8000`

## System Maintenance

### Update Software
```bash
cd ~/flotation-project
git pull
pip3 install -r requirements.txt --upgrade
sudo systemctl restart flotation.service
```

### Backup Data
```bash
# Backup database and logs
tar -czf flotation-backup-$(date +%Y%m%d).tar.gz data/ logs/ config/
```

### Clean Old Data
```bash
# Remove logs older than 30 days
find logs/ -name "*.log" -mtime +30 -delete

# Database auto-cleanup runs daily (configured retention)
```

### Monitor System Health
```bash
# CPU temperature
vcgencmd measure_temp

# Memory usage
free -h

# Disk space
df -h
```

## Safety Guidelines

⚠️ **CRITICAL SAFETY RULES**:

1. **Emergency Stop**: Always functional, test weekly
2. **Pump Limits**: Software limits max duty cycle to 80%
3. **Watchdog Timer**: System halts if vision fails >5 seconds
4. **Manual Override**: Always available regardless of mode
5. **Reagent Monitoring**: Alert when level drops below 20%

## Project Structure

```
flotation-project/
├── config/              # Configuration files
├── src/
│   ├── vision/         # Camera and image processing
│   ├── control/        # PI controller and pump driver
│   ├── ml/             # Anomaly detection
│   ├── api/            # FastAPI backend
│   └── utils/          # Logging, database
├── dashboard/          # Web interface
├── logs/               # Application logs
├── data/               # Database and models
├── tests/              # Unit tests
├── scripts/            # Calibration tools
├── setup.sh            # Installation script
├── requirements.txt    # Python dependencies
└── run.py             # Main application
```

## Support & Documentation

- **GitHub Issues**: Report bugs and feature requests
- **Wiki**: Detailed technical documentation
- **Email**: support@yourproject.com

## License

MIT License - See LICENSE file for details

## Contributors

NUST Flotation Control Project Team

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Platform**: Raspberry Pi 5, Python 3.11+
