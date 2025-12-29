"""
FastAPI Application Entry Point

Main application initialization with CORS, static files, and lifecycle management.
Handles startup/shutdown of vision, control, and anomaly detection systems.
"""

import logging
import asyncio
import numpy as np
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import routes
from . import websocket

logger = logging.getLogger(__name__)

# Global state for system components
system_state = {
    'camera': None,
    'vision_task': None,
    'control_task': None,
    'anomaly_detector': None,
    'metrics_queue': asyncio.Queue(maxsize=100),
    'frame_queue': asyncio.Queue(maxsize=2),
    'running': False,
    'system_health': {
        'cpu_percent': 0.0,
        'memory_percent': 0.0,
        'temperature': 0.0,
        'uptime': 0.0,
        'camera_status': 'unknown',
        'control_status': 'unknown'
    },
    'current_metrics': {
        'bubble_count': 0,
        'avg_bubble_size': 0.0,
        'size_std_dev': 0.0,
        'froth_stability': 0.0,
        'coverage_ratio': 0.0,
        'pump_duty_cycle': 0.0,
        'anomaly_detected': False,
        'timestamp': 0.0
    },
    'control_mode': 'AUTO',  # AUTO or MANUAL
    'control_params': {
        'kp': 0.5,
        'ki': 0.05,
        'setpoint': 120,
        'manual_duty_cycle': 0
    },
    'device_states': {
        'frother': 0,
        'agitator': 50,
        'air_pump': 50,
        'feed_pump': 50
    }
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager - startup and shutdown."""
    logger.info("="*60)
    logger.info("FLOTATION CONTROL SYSTEM - STARTING")
    logger.info("="*60)
    
    # Startup
    try:
        logger.info("Initializing camera...")
        from ..vision.camera import Camera
        system_state['camera'] = Camera(width=640, height=480, fps=15)
        
        if not system_state['camera'].open():
            logger.error("Failed to open camera")
            raise RuntimeError("Camera initialization failed")
        
        logger.info("✓ Camera initialized successfully")
        
        # Initialize anomaly detector (if trained model exists)
        try:
            logger.info("Loading anomaly detector...")
            from ..ml.anomaly_detector import FrothAnomalyDetector
            detector = FrothAnomalyDetector()
            # Check if model exists
            import os
            model_path = "models/anomaly_detector.pkl"
            if os.path.exists(model_path):
                import pickle
                with open(model_path, 'rb') as f:
                    detector.model = pickle.load(f)
                    detector.is_trained = True
                logger.info("✓ Anomaly detector loaded")
            else:
                logger.warning("⚠ No trained anomaly model found - using default")
            system_state['anomaly_detector'] = detector
        except Exception as e:
            logger.warning(f"⚠ Anomaly detector not available: {e}")
            system_state['anomaly_detector'] = None
        
        # Start background tasks
        logger.info("Starting background tasks...")
        system_state['running'] = True
        system_state['vision_task'] = asyncio.create_task(vision_processing_loop())
        system_state['control_task'] = asyncio.create_task(control_loop())
        
        logger.info("✓ System startup complete")
        logger.info("="*60)
        logger.info("Dashboard available at:")
        logger.info("  - Local: http://localhost:8000")
        logger.info("  - Network: http://<raspberry-pi-ip>:8000")
        logger.info("  - Hostname: http://raspberrypi.local:8000")
        logger.info("="*60)
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down system...")
        system_state['running'] = False
        
        # Cancel background tasks
        if system_state['vision_task']:
            system_state['vision_task'].cancel()
            try:
                await system_state['vision_task']
            except asyncio.CancelledError:
                pass
        
        if system_state['control_task']:
            system_state['control_task'].cancel()
            try:
                await system_state['control_task']
            except asyncio.CancelledError:
                pass
        
        # Release camera
        if system_state['camera']:
            system_state['camera'].release()
        
        # Stop pumps
        try:
            from ..control.pump_driver import stop_all_pumps
            stop_all_pumps()
            logger.info("✓ All pumps stopped")
        except Exception as e:
            logger.error(f"Error stopping pumps: {e}")
        
        logger.info("✓ System shutdown complete")


async def vision_processing_loop():
    """Background task for continuous vision processing."""
    from ..vision.froth_analyzer import FrothAnalyzer
    from ..vision.preprocessor import ImagePreprocessor
    from ..vision.bubble_detector import BubbleDetector
    import time
    
    logger.info("Vision processing loop started")
    
    preprocessor = ImagePreprocessor()
    detector = BubbleDetector()
    analyzer = FrothAnalyzer()
    
    while system_state['running']:
        try:
            # Capture frame
            ret, frame = system_state['camera'].read()
            
            if not ret or frame is None:
                logger.warning("Failed to capture frame")
                await asyncio.sleep(0.1)
                continue
            
            # Process frame - use correct method names
            processed = preprocessor.process(frame)
            binary_mask = processed.get('closing', processed.get('binary'))
            
            if binary_mask is None:
                logger.warning("Preprocessing failed")
                await asyncio.sleep(0.1)
                continue
            
            bubble_data = detector.detect(binary_mask, frame)
            
            # Extract metrics from bubble detection
            metrics = {
                'bubble_count': bubble_data['count'],
                'avg_bubble_size': bubble_data.get('avg_diameter', 0.0),
                'size_std_dev': np.std(bubble_data['diameters']) if bubble_data['diameters'] else 0.0,
                'coverage_ratio': len(bubble_data['diameters']) / max(frame.shape[0] * frame.shape[1] / 1000, 1),
                'froth_stability': 0.0  # Can be calculated from analyzer history
            }
            
            # Check for anomalies
            if system_state['anomaly_detector'] and system_state['anomaly_detector'].is_trained:
                features = [
                    metrics['bubble_count'],
                    metrics['avg_bubble_size'],
                    metrics['size_std_dev'],
                    metrics['coverage_ratio']
                ]
                anomaly = system_state['anomaly_detector'].predict(features)
                metrics['anomaly_detected'] = (anomaly == -1)
            else:
                metrics['anomaly_detected'] = False
            
            metrics['timestamp'] = time.time()
            
            # Update global state
            system_state['current_metrics'].update(metrics)
            system_state['system_health']['camera_status'] = 'active'
            
            # Send to queues (non-blocking)
            try:
                system_state['metrics_queue'].put_nowait(metrics.copy())
            except asyncio.QueueFull:
                pass  # Skip if queue full
            
            # Send annotated frame to WebSocket queue
            # Create annotated frame with detected bubbles
            annotated_frame = frame.copy()
            if 'markers' in bubble_data:
                # Draw bubble markers on frame
                import cv2 as cv
                markers = bubble_data['markers']
                annotated_frame[markers > 1] = [0, 255, 0]  # Green overlay for bubbles
            
            if annotated_frame is not None:
                try:
                    system_state['frame_queue'].put_nowait(annotated_frame)
                except asyncio.QueueFull:
                    # Remove old frame and add new one
                    try:
                        system_state['frame_queue'].get_nowait()
                        system_state['frame_queue'].put_nowait(annotated_frame)
                    except:
                        pass
            
            # Limit processing rate to ~10 FPS
            await asyncio.sleep(0.1)
            
        except asyncio.CancelledError:
            logger.info("Vision processing loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in vision processing: {e}", exc_info=True)
            system_state['system_health']['camera_status'] = 'error'
            await asyncio.sleep(1)  # Prevent tight error loop


async def control_loop():
    """Background task for PI control loop."""
    from ..control.pi_controller import PIController
    from ..control.pump_driver import PumpDriver
    import time
    
    logger.info("Control loop started")
    
    # Initialize components
    pi_controller = PIController(
        kp=system_state['control_params']['kp'],
        ki=system_state['control_params']['ki'],
        setpoint=system_state['control_params']['setpoint']
    )
    
    pump_driver = PumpDriver()
    last_update = time.time()
    
    while system_state['running']:
        try:
            current_time = time.time()
            dt = current_time - last_update
            last_update = current_time
            
            if system_state['control_mode'] == 'AUTO':
                # Automatic control
                measured_value = system_state['current_metrics']['bubble_count']
                
                # Update PI parameters if changed
                pi_controller.kp = system_state['control_params']['kp']
                pi_controller.ki = system_state['control_params']['ki']
                pi_controller.setpoint = system_state['control_params']['setpoint']
                
                # Calculate control output
                duty_cycle = pi_controller.update(measured_value, dt)
                
                # Apply to frother pump
                pump_driver.set_duty_cycle('frother', duty_cycle)
                system_state['current_metrics']['pump_duty_cycle'] = duty_cycle
                system_state['device_states']['frother'] = duty_cycle
                
            else:
                # Manual control
                duty_cycle = system_state['control_params']['manual_duty_cycle']
                pump_driver.set_duty_cycle('frother', duty_cycle)
                system_state['current_metrics']['pump_duty_cycle'] = duty_cycle
                system_state['device_states']['frother'] = duty_cycle
            
            # Control other devices (agitator, air, feed)
            pump_driver.set_duty_cycle('agitator', system_state['device_states']['agitator'])
            pump_driver.set_duty_cycle('air_pump', system_state['device_states']['air_pump'])
            pump_driver.set_duty_cycle('feed_pump', system_state['device_states']['feed_pump'])
            
            system_state['system_health']['control_status'] = 'active'
            
            # Control loop runs at 1 Hz
            await asyncio.sleep(1.0)
            
        except asyncio.CancelledError:
            logger.info("Control loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in control loop: {e}", exc_info=True)
            system_state['system_health']['control_status'] = 'error'
            await asyncio.sleep(1)


# Create FastAPI application
app = FastAPI(
    title="Flotation Control System API",
    description="REST API and WebSocket server for froth flotation control",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins on local network
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api")
app.include_router(websocket.router)

# Mount static files (dashboard)
dashboard_path = Path(__file__).parent.parent.parent / "dashboard"
app.mount("/static", StaticFiles(directory=str(dashboard_path)), name="static")


@app.get("/")
async def root():
    """Serve the dashboard HTML."""
    dashboard_file = dashboard_path / "index.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return {"message": "Flotation Control System API", "status": "running"}


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "camera": system_state['system_health']['camera_status'],
        "control": system_state['system_health']['control_status']
    }


# Export system state for routes and websocket modules
def get_system_state():
    """Get reference to system state."""
    return system_state
