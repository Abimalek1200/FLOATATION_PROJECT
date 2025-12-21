"""
REST API Routes for Flotation Control System

Provides endpoints for:
- Metrics retrieval
- Control parameters
- System status
- Configuration management
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["api"])


# Pydantic models for request/response validation
class MetricsResponse(BaseModel):
    """Current froth metrics."""
    bubble_count: int = Field(..., description="Number of bubbles detected")
    avg_bubble_size: float = Field(..., description="Average bubble size in pixels²")
    size_std_dev: float = Field(..., description="Bubble size standard deviation")
    froth_stability: float = Field(..., ge=0, le=1, description="Froth stability score (0-1)")
    coverage_ratio: float = Field(..., ge=0, le=1, description="Bubble coverage ratio")
    pump_duty_cycle: float = Field(..., ge=0, le=100, description="Frother pump duty cycle (%)")
    anomaly_detected: bool = Field(..., description="Anomaly detection flag")
    timestamp: float = Field(..., description="Unix timestamp")


class ControlMode(BaseModel):
    """Control mode setting."""
    mode: str = Field(..., pattern="^(AUTO|MANUAL)$", description="Control mode: AUTO or MANUAL")


class SetpointUpdate(BaseModel):
    """Update control setpoint."""
    setpoint: int = Field(..., ge=0, le=500, description="Target bubble count")


class PIGainsUpdate(BaseModel):
    """Update PI controller gains."""
    kp: float = Field(..., ge=0, le=10, description="Proportional gain")
    ki: float = Field(..., ge=0, le=1, description="Integral gain")


class ManualControl(BaseModel):
    """Manual pump control."""
    duty_cycle: float = Field(..., ge=0, le=100, description="Pump duty cycle (0-100%)")


class DeviceControl(BaseModel):
    """Control for agitator, air pump, feed pump."""
    device: str = Field(..., pattern="^(agitator|air_pump|feed_pump)$")
    duty_cycle: float = Field(..., ge=0, le=100, description="Duty cycle (0-100%)")


class SystemStatus(BaseModel):
    """System health and status."""
    cpu_percent: float
    memory_percent: float
    temperature: float
    uptime: float
    camera_status: str
    control_status: str
    control_mode: str


class DataRetentionUpdate(BaseModel):
    """Update data retention period."""
    retention_days: int = Field(..., ge=1, le=365, description="Data retention in days")


# Helper function to get system state
def get_state() -> Dict[str, Any]:
    """Import and return system state from main module."""
    from .main import get_system_state
    return get_system_state()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get current froth metrics.
    
    Returns real-time measurements from vision processing and control system.
    """
    try:
        state = get_state()
        return state['current_metrics']
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )


@router.get("/status", response_model=SystemStatus)
async def get_status():
    """Get system health and status information.
    
    Returns CPU, memory, temperature, and component status.
    """
    try:
        state = get_state()
        
        # Update system metrics
        import psutil
        state['system_health']['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        state['system_health']['memory_percent'] = psutil.virtual_memory().percent
        
        # Get temperature (Raspberry Pi specific)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                state['system_health']['temperature'] = temp
        except:
            state['system_health']['temperature'] = 0.0
        
        # Calculate uptime
        state['system_health']['uptime'] = time.time() - psutil.boot_time()
        
        return {
            **state['system_health'],
            'control_mode': state['control_mode']
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status: {str(e)}"
        )


@router.post("/mode")
async def set_control_mode(mode: ControlMode):
    """Set control mode (AUTO or MANUAL).
    
    AUTO: PI controller manages frother pump based on bubble count.
    MANUAL: Operator directly controls pump duty cycle.
    """
    try:
        state = get_state()
        old_mode = state['control_mode']
        state['control_mode'] = mode.mode
        
        logger.info(f"Control mode changed: {old_mode} → {mode.mode}")
        
        return {
            "status": "success",
            "message": f"Control mode set to {mode.mode}",
            "previous_mode": old_mode,
            "current_mode": mode.mode
        }
    except Exception as e:
        logger.error(f"Error setting control mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set control mode: {str(e)}"
        )


@router.post("/setpoint")
async def update_setpoint(update: SetpointUpdate):
    """Update PI controller setpoint (target bubble count).
    
    Only applies in AUTO mode.
    """
    try:
        state = get_state()
        old_setpoint = state['control_params']['setpoint']
        state['control_params']['setpoint'] = update.setpoint
        
        logger.info(f"Setpoint updated: {old_setpoint} → {update.setpoint}")
        
        return {
            "status": "success",
            "message": f"Setpoint updated to {update.setpoint}",
            "previous": old_setpoint,
            "current": update.setpoint,
            "mode": state['control_mode']
        }
    except Exception as e:
        logger.error(f"Error updating setpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setpoint: {str(e)}"
        )


@router.post("/pi-gains")
async def update_pi_gains(gains: PIGainsUpdate):
    """Update PI controller gains (Kp and Ki).
    
    Use with caution - improper values can cause instability.
    """
    try:
        state = get_state()
        old_kp = state['control_params']['kp']
        old_ki = state['control_params']['ki']
        
        state['control_params']['kp'] = gains.kp
        state['control_params']['ki'] = gains.ki
        
        logger.info(f"PI gains updated: Kp {old_kp}→{gains.kp}, Ki {old_ki}→{gains.ki}")
        
        return {
            "status": "success",
            "message": "PI gains updated",
            "previous": {"kp": old_kp, "ki": old_ki},
            "current": {"kp": gains.kp, "ki": gains.ki}
        }
    except Exception as e:
        logger.error(f"Error updating PI gains: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update PI gains: {str(e)}"
        )


@router.post("/manual-control")
async def manual_control(control: ManualControl):
    """Set manual pump duty cycle.
    
    Only applies in MANUAL mode. Use with caution.
    """
    try:
        state = get_state()
        
        if state['control_mode'] != 'MANUAL':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manual control only available in MANUAL mode"
            )
        
        old_duty = state['control_params']['manual_duty_cycle']
        state['control_params']['manual_duty_cycle'] = control.duty_cycle
        
        logger.info(f"Manual duty cycle: {old_duty}% → {control.duty_cycle}%")
        
        return {
            "status": "success",
            "message": f"Manual duty cycle set to {control.duty_cycle}%",
            "previous": old_duty,
            "current": control.duty_cycle
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual control: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set manual control: {str(e)}"
        )


@router.post("/device-control")
async def control_device(control: DeviceControl):
    """Control agitator, air pump, or feed pump.
    
    Available in both AUTO and MANUAL modes.
    """
    try:
        state = get_state()
        
        old_duty = state['device_states'].get(control.device, 0)
        state['device_states'][control.device] = control.duty_cycle
        
        logger.info(f"{control.device} duty cycle: {old_duty}% → {control.duty_cycle}%")
        
        return {
            "status": "success",
            "message": f"{control.device} set to {control.duty_cycle}%",
            "device": control.device,
            "previous": old_duty,
            "current": control.duty_cycle
        }
    except Exception as e:
        logger.error(f"Error controlling device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control device: {str(e)}"
        )


@router.post("/emergency-stop")
async def emergency_stop():
    """Emergency stop - immediately halt all pumps and motors.
    
    Switches to MANUAL mode with 0% duty cycle on all devices.
    """
    try:
        state = get_state()
        
        # Stop all devices
        from ..control.pump_driver import stop_all_pumps
        stop_all_pumps()
        
        # Update state
        state['control_mode'] = 'MANUAL'
        state['control_params']['manual_duty_cycle'] = 0
        state['device_states'] = {
            'frother': 0,
            'agitator': 0,
            'air_pump': 0,
            'feed_pump': 0
        }
        
        logger.warning("EMERGENCY STOP activated")
        
        return {
            "status": "success",
            "message": "Emergency stop activated - all devices halted",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency stop failed: {str(e)}"
        )


@router.get("/config")
async def get_config():
    """Get current system configuration."""
    try:
        state = get_state()
        return {
            "control_mode": state['control_mode'],
            "control_params": state['control_params'],
            "device_states": state['device_states'],
            "camera_settings": {
                "width": state['camera'].width if state['camera'] else 640,
                "height": state['camera'].height if state['camera'] else 480,
                "fps": state['camera'].fps if state['camera'] else 15
            }
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve config: {str(e)}"
        )


@router.get("/history")
async def get_history(limit: int = 100):
    """Get recent metrics history.
    
    Args:
        limit: Maximum number of records to return (default 100, max 1000)
    """
    try:
        if limit > 1000:
            limit = 1000
        
        # Get metrics from queue
        state = get_state()
        history = []
        
        # Note: This is a simplified implementation
        # In production, you'd query from SQLite database
        # For now, return current metrics as single point
        history.append(state['current_metrics'])
        
        return {
            "count": len(history),
            "limit": limit,
            "data": history
        }
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.post("/snapshot")
async def save_snapshot():
    """Save current frame as snapshot image."""
    try:
        import cv2 as cv
        from datetime import datetime
        import os
        
        state = get_state()
        
        # Get current frame
        if state['camera'] is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Camera not available"
            )
        
        ret, frame = state['camera'].read()
        
        if not ret or frame is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to capture frame"
            )
        
        # Save snapshot
        snapshot_dir = "snapshots"
        os.makedirs(snapshot_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        filepath = os.path.join(snapshot_dir, filename)
        
        cv.imwrite(filepath, frame)
        
        logger.info(f"Snapshot saved: {filepath}")
        
        return {
            "status": "success",
            "message": "Snapshot saved",
            "filename": filename,
            "path": filepath,
            "timestamp": timestamp
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save snapshot: {str(e)}"
        )
