"""
USB Camera Interface for Flotation Control System

Handles camera initialization, frame capture, and error recovery.
Optimized for Raspberry Pi 5 with USB webcam.
"""

import cv2 as cv
import numpy as np
import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class Camera:
    """USB webcam interface with robust initialization and error handling."""
    
    def __init__(
        self,
        device_id: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        max_retries: int = 5
    ):
        """Initialize camera interface.
        
        Args:
            device_id: Camera device ID (usually 0 for first USB camera)
            width: Frame width in pixels (640 for performance, 1920 for quality)
            height: Frame height in pixels (480 for performance, 1080 for quality)
            fps: Target frames per second (10-30 recommended)
            max_retries: Maximum initialization retry attempts
        """
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.max_retries = max_retries
        self.cap: Optional[cv.VideoCapture] = None
        self.is_opened = False
        self.frame_count = 0
        self.last_frame_time = time.time()
        
    def open(self) -> bool:
        """Open camera connection with retry logic.
        
        Returns:
            True if camera opened successfully, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting to open camera (attempt {attempt + 1}/{self.max_retries})")
                
                # Initialize camera
                self.cap = cv.VideoCapture(self.device_id)
                
                if not self.cap.isOpened():
                    logger.warning(f"Camera init failed on attempt {attempt + 1}")
                    time.sleep(2)
                    continue
                
                # Configure camera settings
                self.cap.set(cv.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv.CAP_PROP_FPS, self.fps)
                
                # Verify settings were applied
                actual_width = int(self.cap.get(cv.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv.CAP_PROP_FRAME_HEIGHT))
                actual_fps = int(self.cap.get(cv.CAP_PROP_FPS))
                
                logger.info(
                    f"Camera opened: {actual_width}x{actual_height} @ {actual_fps}fps"
                )
                
                # Test frame capture
                ret, test_frame = self.cap.read()
                if not ret or test_frame is None:
                    logger.warning("Camera opened but cannot read frames")
                    self.cap.release()
                    time.sleep(2)
                    continue
                
                self.is_opened = True
                logger.info("Camera initialization successful")
                return True
                
            except Exception as e:
                logger.error(f"Camera initialization error: {e}")
                if self.cap:
                    self.cap.release()
                time.sleep(2)
        
        logger.error(f"Failed to open camera after {self.max_retries} attempts")
        return False
    
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a frame from the camera.
        
        Returns:
            Tuple of (success, frame) where frame is BGR numpy array or None
        """
        if not self.is_opened or self.cap is None:
            logger.warning("Camera not opened, attempting to open...")
            if not self.open():
                return False, None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                logger.warning("Failed to read frame from camera")
                self.is_opened = False
                return False, None
            
            # Update frame statistics
            self.frame_count += 1
            self.last_frame_time = time.time()
            
            return True, frame
            
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            self.is_opened = False
            return False, None
    
    def get_frame_rate(self) -> float:
        """Calculate actual frame rate based on recent captures.
        
        Returns:
            Frames per second (estimated from last 30 frames)
            
        Example:
            >>> fps = camera.get_frame_rate()
            >>> print(f"Running at {fps:.1f} FPS")
        """
        if not hasattr(self, '_frame_times'):
            self._frame_times = []
        
        # Record current time
        self._frame_times.append(time.time())
        
        # Keep only recent 30 timestamps (prevents memory growth)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)
        
        # Need at least 2 points to calculate rate
        if len(self._frame_times) < 2:
            return 0.0
        
        # FPS = frames / time_elapsed
        elapsed = self._frame_times[-1] - self._frame_times[0]
        return (len(self._frame_times) - 1) / elapsed if elapsed > 0 else 0.0
    
    def is_healthy(self) -> bool:
        """Check if camera is operating normally.
        
        Returns:
            True if camera is healthy (capturing frames at acceptable rate)
        """
        if not self.is_opened:
            return False
        
        # Check if we've received frames recently (within last 5 seconds)
        time_since_last_frame = time.time() - self.last_frame_time
        if time_since_last_frame > 5.0:
            logger.warning(f"No frames received for {time_since_last_frame:.1f}s")
            return False
        
        # Check frame rate
        fps = self.get_frame_rate()
        if fps < 5.0 and self.frame_count > 30:
            logger.warning(f"Low frame rate: {fps:.1f} FPS")
            return False
        
        return True
    
    def release(self):
        """Release camera resources."""
        if self.cap:
            logger.info("Releasing camera")
            self.cap.release()
            self.cap = None
        self.is_opened = False
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
    
    def __del__(self):
        """Destructor to ensure camera is released."""
        self.release()


def robust_camera_init(
    device_id: int = 0,
    width: int = 640,
    height: int = 480,
    fps: int = 30,
    max_retries: int = 5
) -> Optional[Camera]:
    """Helper function for robust camera initialization.
    
    Args:
        device_id: Camera device ID (0 for first USB camera)
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Target frames per second
        max_retries: Maximum initialization attempts
    
    Returns:
        Camera instance if successful, None otherwise
    """
    camera = Camera(
        device_id=device_id,
        width=width,
        height=height,
        fps=fps,
        max_retries=max_retries
    )
    
    if camera.open():
        return camera
    
    return None


if __name__ == "__main__":
    # Test camera initialization
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing camera initialization...")
    camera = robust_camera_init()
    
    if camera:
        print("Camera opened successfully!")
        print(f"Capturing 10 test frames...")
        
        for i in range(10):
            ret, frame = camera.read()
            if ret:
                print(f"Frame {i+1}: {frame.shape}, FPS: {camera.get_frame_rate():.1f}")
            else:
                print(f"Frame {i+1}: Failed to read")
            time.sleep(0.1)
        
        camera.release()
        print("Camera test completed")
    else:
        print("Failed to open camera")
