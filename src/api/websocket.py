"""
WebSocket Handler for Real-time Streaming

Provides WebSocket endpoints for:
- Video frame streaming
- Real-time metrics updates
- System alerts and notifications
"""

import logging
import asyncio
import json
import base64
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2 as cv
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time data streaming.
    
    Sends:
    - Video frames (JPEG encoded, base64)
    - Metrics updates (JSON)
    - Anomaly alerts
    - System status updates
    """
    await manager.connect(websocket)
    
    # Get system state
    from .main import get_system_state
    state = get_system_state()
    
    # Send initial connection success message
    await manager.send_personal({
        "type": "connected",
        "message": "WebSocket connection established",
        "timestamp": asyncio.get_event_loop().time()
    }, websocket)
    
    # Create tasks for streaming
    frame_task = asyncio.create_task(stream_frames(websocket, state))
    metrics_task = asyncio.create_task(stream_metrics(websocket, state))
    
    try:
        # Listen for incoming messages (client commands)
        while True:
            try:
                data = await websocket.receive_json()
                await handle_client_message(data, websocket, state)
            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break
    
    finally:
        # Cleanup
        frame_task.cancel()
        metrics_task.cancel()
        
        try:
            await frame_task
        except asyncio.CancelledError:
            pass
        
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass
        
        manager.disconnect(websocket)


async def stream_frames(websocket: WebSocket, state: dict):
    """Stream video frames to client at ~10 FPS."""
    try:
        while True:
            try:
                # Get frame from queue (non-blocking)
                frame = await asyncio.wait_for(
                    state['frame_queue'].get(),
                    timeout=1.0
                )
                
                # Encode frame as JPEG
                _, buffer = cv.imencode('.jpg', frame, [cv.IMWRITE_JPEG_QUALITY, 70])
                
                # Convert to base64
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send to client
                await websocket.send_json({
                    "type": "frame",
                    "image": frame_base64,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                # Limit to ~10 FPS
                await asyncio.sleep(0.1)
                
            except asyncio.TimeoutError:
                # No frame available, continue
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error streaming frame: {e}")
                await asyncio.sleep(0.5)
    
    except asyncio.CancelledError:
        logger.info("Frame streaming cancelled")
        raise


async def stream_metrics(websocket: WebSocket, state: dict):
    """Stream metrics updates to client at ~1 Hz."""
    last_anomaly = False
    
    try:
        while True:
            try:
                # Send current metrics
                metrics = state['current_metrics'].copy()
                
                await websocket.send_json({
                    "type": "metrics",
                    "data": metrics
                })
                
                # Check for anomaly and send alert if detected
                if metrics.get('anomaly_detected', False) and not last_anomaly:
                    await websocket.send_json({
                        "type": "anomaly",
                        "severity": "warning",
                        "message": "Anomaly detected in froth characteristics",
                        "metrics": {
                            "bubble_count": metrics['bubble_count'],
                            "avg_size": metrics['avg_bubble_size'],
                            "stability": metrics['froth_stability']
                        },
                        "timestamp": metrics['timestamp']
                    })
                
                last_anomaly = metrics.get('anomaly_detected', False)
                
                # Send control status
                await websocket.send_json({
                    "type": "control",
                    "mode": state['control_mode'],
                    "setpoint": state['control_params']['setpoint'],
                    "pump_duty_cycle": metrics['pump_duty_cycle'],
                    "device_states": state['device_states'],
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                # Update every second
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error streaming metrics: {e}")
                await asyncio.sleep(1.0)
    
    except asyncio.CancelledError:
        logger.info("Metrics streaming cancelled")
        raise


async def handle_client_message(data: dict, websocket: WebSocket, state: dict):
    """Handle incoming messages from WebSocket client.
    
    Supports:
    - Ping/pong for keepalive
    - Control commands (mode changes, setpoint updates)
    - Snapshot requests
    """
    try:
        msg_type = data.get('type')
        
        if msg_type == 'ping':
            # Respond to keepalive ping
            await websocket.send_json({
                "type": "pong",
                "timestamp": asyncio.get_event_loop().time()
            })
        
        elif msg_type == 'set_mode':
            # Change control mode
            mode = data.get('mode', 'AUTO')
            if mode in ['AUTO', 'MANUAL']:
                state['control_mode'] = mode
                logger.info(f"Control mode set to {mode} via WebSocket")
                
                await websocket.send_json({
                    "type": "mode_changed",
                    "mode": mode,
                    "status": "success"
                })
        
        elif msg_type == 'set_setpoint':
            # Update setpoint
            setpoint = data.get('value', 120)
            if 0 <= setpoint <= 500:
                state['control_params']['setpoint'] = setpoint
                logger.info(f"Setpoint set to {setpoint} via WebSocket")
                
                await websocket.send_json({
                    "type": "setpoint_changed",
                    "value": setpoint,
                    "status": "success"
                })
        
        elif msg_type == 'snapshot':
            # Save snapshot
            await websocket.send_json({
                "type": "snapshot_saved",
                "status": "success",
                "message": "Snapshot request received"
            })
        
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    except Exception as e:
        logger.error(f"Error handling client message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for streaming system logs.
    
    Useful for real-time monitoring and debugging.
    """
    await websocket.accept()
    logger.info("Log streaming client connected")
    
    try:
        # This is a simplified implementation
        # In production, you'd tail the log file or use a log handler
        
        while True:
            # Send periodic log messages
            await websocket.send_json({
                "type": "log",
                "level": "INFO",
                "message": "System operating normally",
                "timestamp": asyncio.get_event_loop().time()
            })
            
            await asyncio.sleep(5.0)
    
    except WebSocketDisconnect:
        logger.info("Log streaming client disconnected")
    except Exception as e:
        logger.error(f"Error in log streaming: {e}")


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for critical alerts only.
    
    Sends:
    - Anomaly detections
    - System errors
    - Hardware failures
    - Emergency stops
    """
    await websocket.accept()
    logger.info("Alert streaming client connected")
    
    # Get system state
    from .main import get_system_state
    state = get_system_state()
    
    try:
        last_anomaly_check = False
        
        while True:
            # Check for anomalies
            if state['current_metrics'].get('anomaly_detected', False):
                if not last_anomaly_check:
                    # New anomaly detected
                    await websocket.send_json({
                        "type": "alert",
                        "severity": "warning",
                        "category": "anomaly",
                        "message": "Froth anomaly detected",
                        "data": state['current_metrics'],
                        "timestamp": asyncio.get_event_loop().time()
                    })
                last_anomaly_check = True
            else:
                last_anomaly_check = False
            
            # Check system health
            if state['system_health']['camera_status'] == 'error':
                await websocket.send_json({
                    "type": "alert",
                    "severity": "error",
                    "category": "hardware",
                    "message": "Camera system error",
                    "timestamp": asyncio.get_event_loop().time()
                })
            
            if state['system_health']['control_status'] == 'error':
                await websocket.send_json({
                    "type": "alert",
                    "severity": "error",
                    "category": "control",
                    "message": "Control system error",
                    "timestamp": asyncio.get_event_loop().time()
                })
            
            # Check CPU temperature
            temp = state['system_health'].get('temperature', 0)
            if temp > 75:
                await websocket.send_json({
                    "type": "alert",
                    "severity": "warning",
                    "category": "system",
                    "message": f"High CPU temperature: {temp:.1f}°C",
                    "timestamp": asyncio.get_event_loop().time()
                })
            
            await asyncio.sleep(2.0)
    
    except WebSocketDisconnect:
        logger.info("Alert streaming client disconnected")
    except Exception as e:
        logger.error(f"Error in alert streaming: {e}")
