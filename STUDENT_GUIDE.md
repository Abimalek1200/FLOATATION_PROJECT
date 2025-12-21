# Flotation Control System - Student Guide

## 📚 What You've Built

A complete vision-controlled flotation system that:
- **Sees** froth bubbles with a camera
- **Thinks** using PI control + machine learning  
- **Acts** by adjusting reagent pumps
- **Monitors** everything through a web dashboard

## 🎯 Learning Objectives

This project teaches you:
1. **Computer Vision** - Image processing with OpenCV
2. **Control Systems** - PI controller for automation
3. **Machine Learning** - Anomaly detection
4. **Web Development** - Real-time dashboards
5. **Hardware Control** - GPIO, PWM, safety systems
6. **System Integration** - Making it all work together!

## 📁 Code Organization

### Vision Module (`src/vision/`)
**What it does**: Captures camera frames and detects bubbles

- **camera.py** - Talks to USB webcam, handles errors
  - Key function: `camera.read()` → gets one frame
  - Student tip: Check `is_healthy()` to monitor camera
  
- **preprocessor.py** - Cleans up images for bubble detection
  - Converts color → grayscale → binary (black & white)
  - Each step explained with "Why" comments
  
- **bubble_detector.py** - Finds and counts bubbles
  - Uses "watershed" algorithm (like filling a basin with water)
  - Returns: count, sizes, positions
  
- **froth_analyzer.py** - Calculates overall froth quality
  - Combines bubble data into useful metrics
  - Tracks stability over time

### Control Module (`src/control/`)
**What it does**: Automatically adjusts pumps to maintain target

- **pi_controller.py** - THE BRAIN 🧠
  - **Proportional (P)**: React to current error
  - **Integral (I)**: Fix persistent offset
  - Student-friendly: Every variable explained!
  
- **pump_driver.py** - Sends PWM signals to pumps
  - Uses `lgpio` library (Raspberry Pi 5)
  - Safety: Max 80% duty cycle (prevents overdosing)
  
- **safety.py** - Watchdog and emergency stop
  - Monitors vision + control systems
  - Auto-stops if anything fails > 5 seconds

### Machine Learning (`src/ml/`)
**What it does**: Detects unusual froth behavior

- **anomaly_detector.py** - Finds outliers
  - Uses Isolation Forest (fast, works on RPi)
  - Train once on good data → detects bad data forever
  - Example code included for testing

### API Backend (`src/api/`)
**What it does**: Connects everything to the dashboard

- **main.py** - Application startup/shutdown
  - Starts camera, vision loop, control loop
  - Manages system state (metrics, settings)
  
- **routes.py** - REST API endpoints
  - GET /api/metrics → current measurements
  - POST /api/setpoint → change target
  - POST /api/emergency-stop → PANIC BUTTON
  
- **websocket.py** - Real-time streaming
  - Sends video frames + metrics to dashboard
  - ~10 FPS video, 1 Hz metrics

### Utilities (`src/utils/`)
**What it does**: Logging and data storage

- **logger.py** - Organized logging
  - Everything goes to `logs/` folder
  - Automatic file rotation (saves space)
  
- **data_manager.py** - SQLite database
  - Stores all metrics with timestamps
  - Auto-cleanup after 7 days (configurable)

## 🔧 How It All Works Together

```
Camera → Vision → Metrics → PI Controller → Pump → Froth
   ↓                           ↓
Dashboard ←─── WebSocket ──── API Server
```

### The Main Loop (1 second cycle):
1. Camera captures frame
2. Vision finds bubbles → count = 95
3. PI controller: "Target is 120, I'm 25 short!"
4. Calculate: increase pump to 55%
5. Send PWM signal to pump
6. Wait 1 second, repeat

## 🎓 Student-Friendly Features

### Clear Variable Names
```python
# ❌ Bad (confusing)
bc = detect(img)

# ✅ Good (obvious)
bubble_count = detect_bubbles(frame)
```

### Step-by-Step Comments
```python
# Step 1: Convert to grayscale (easier to process)
gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

# Step 2: Remove noise with blur
blurred = cv.GaussianBlur(gray, (1, 1), 0)

# Step 3: Convert to binary (black/white only)
_, binary = cv.threshold(blurred, 0, 255, cv.THRESH_BINARY_INV)
```

### Examples in Every Function
```python
def set_pump_rate(duty_cycle: float):
    """Set pump PWM duty cycle.
    
    Args:
        duty_cycle: 0-100 (percentage)
    
    Example:
        >>> set_pump_rate(50)  # Half speed
        >>> set_pump_rate(0)   # Stop pump
    """
```

### Built-in Tests
Every module has a `if __name__ == "__main__":` section you can run!

```bash
# Test the camera module
python3 src/vision/camera.py

# Test the PI controller
python3 src/control/pi_controller.py

# Test anomaly detection
python3 src/ml/anomaly_detector.py
```

## 🚀 Running the System

### On Raspberry Pi:
```bash
cd ~/FLOATATION_PROJECT

# Start the system
python3 run.py

# Or use systemd service
sudo systemctl start flotation.service
```

### Access Dashboard:
- From Pi: http://localhost:8000
- From phone: http://raspberrypi.local:8000
- From laptop: http://192.168.1.100:8000 (Pi's IP)

## 🐛 Debugging Tips

### Camera not working?
```bash
# Check if camera is detected
ls /dev/video*

# Test camera directly
python3 -c "import cv2; cap=cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

### Logs are your friend!
```bash
# Watch logs in real-time
tail -f logs/flotation.log

# See only errors
tail -f logs/flotation-error.log

# Search for specific issue
grep "error" logs/flotation.log
```

### Import errors (lgpio, psutil)?
- Normal on Windows! These only work on Raspberry Pi
- Run `setup.sh` on the Pi to install them

## 📊 Understanding the Code

### Why PI Control?
- **P (Proportional)**: Quick response to errors
  - Error = 25 bubbles short → P says "increase pump 25%"
- **I (Integral)**: Fixes persistent offsets
  - Been low for 10 seconds → I says "add extra 5%"
- Together: Fast response + no steady error!

### Why Isolation Forest?
- Traditional rules: "If bubbles > 150, alert"
  - Problem: What if normal changes?
- Isolation Forest: Learns what's normal
  - Adapts to your specific system
  - Finds weird patterns automatically

### Why Async (FastAPI)?
- Handles multiple clients without blocking
- Vision loop runs while API serves requests
- WebSocket streams while REST API responds

## 🎯 Next Steps for Students

1. **Understand one module at a time**
   - Start with `camera.py` (simplest)
   - Move to `pi_controller.py` (core logic)
   - Then `main.py` (how it connects)

2. **Modify and experiment**
   - Change PI gains → see oscillation vs sluggishness
   - Adjust bubble detection thresholds
   - Try different contamination values in anomaly detector

3. **Add features**
   - Email alerts when anomaly detected
   - Data export to CSV
   - Better PI auto-tuning
   - Additional sensors (pH, temperature)

4. **Optimize performance**
   - Profile code to find slow parts
   - Reduce image resolution if CPU high
   - Tune database cleanup frequency

## 💡 Key Concepts to Master

1. **Feedback Control**: Output affects input
2. **Image Processing Pipeline**: Raw → Gray → Binary → Features
3. **Async Programming**: Multiple tasks at once
4. **Real-time Systems**: Deadlines matter!
5. **Safety-Critical Code**: Always have a backup plan

## 📚 Further Reading

- OpenCV tutorials: https://docs.opencv.org/
- PI tuning guide: Ziegler-Nichols method
- Isolation Forest paper: Liu et al. 2008
- FastAPI docs: https://fastapi.tiangolo.com/

## ✅ Success Criteria

You understand the code when you can:
- [ ] Explain what each file does in one sentence
- [ ] Trace data flow from camera to pump
- [ ] Modify PI gains and predict behavior
- [ ] Add a new metric to the dashboard
- [ ] Debug a vision processing error
- [ ] Explain why safety systems are critical

---

**Remember**: This code is designed for learning. Every function has:
- ✅ Clear purpose
- ✅ Type hints
- ✅ Examples
- ✅ Comments explaining WHY

**Read the code top-to-bottom like a book!** 📖

Good luck, and enjoy building industrial automation systems! 🏭✨
