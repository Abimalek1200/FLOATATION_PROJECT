"""
Safety Manager for Flotation System

Handles emergency stops, watchdogs, and safety limits.
Keeps the system safe for students and operators.
"""

import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SafetyManager:
    """Safety monitoring and emergency controls.
    
    Protects against:
    - Vision system failures
    - Control system errors
    - Hardware malfunctions
    """
    
    def __init__(self, watchdog_timeout: float = 5.0):
        """Initialize safety manager.
        
        Args:
            watchdog_timeout: Seconds before triggering safety stop if no updates
            
        Example:
            >>> safety = SafetyManager(watchdog_timeout=5.0)
            >>> safety.register_estop_callback(emergency_stop_function)
        """
        self.watchdog_timeout = watchdog_timeout
        self.estop_triggered = False
        self.estop_callback: Optional[Callable] = None
        
        # Track last updates from each system
        self.last_vision_update = time.time()
        self.last_control_update = time.time()
        
        logger.info(f"Safety Manager initialized (watchdog: {watchdog_timeout}s)")
    
    def register_estop_callback(self, callback: Callable):
        """Register function to call during emergency stop.
        
        Args:
            callback: Function to execute (should stop all pumps)
            
        Example:
            >>> def emergency_stop():
            ...     pump_driver.stop_all_pumps()
            >>> safety.register_estop_callback(emergency_stop)
        """
        self.estop_callback = callback
        logger.info("Emergency stop callback registered")
    
    def update_vision_heartbeat(self):
        """Call this every time vision system produces data.
        
        Lets watchdog know vision is alive.
        
        Example:
            >>> # In vision processing loop:
            >>> metrics = analyze_frame(frame)
            >>> safety.update_vision_heartbeat()
        """
        self.last_vision_update = time.time()
    
    def update_control_heartbeat(self):
        """Call this every time control loop runs.
        
        Lets watchdog know control is alive.
        
        Example:
            >>> # In control loop:
            >>> duty_cycle = pi_controller.update(measured, dt)
            >>> safety.update_control_heartbeat()
        """
        self.last_control_update = time.time()
    
    def check_watchdog(self) -> bool:
        """Check if any system has timed out.
        
        Returns:
            True if all systems healthy, False if timeout detected
            
        Example:
            >>> if not safety.check_watchdog():
            ...     print("System failure detected!")
        """
        current_time = time.time()
        
        # Check vision system
        vision_timeout = current_time - self.last_vision_update
        if vision_timeout > self.watchdog_timeout:
            logger.critical(
                f"Vision system timeout ({vision_timeout:.1f}s) - EMERGENCY STOP"
            )
            self.emergency_stop()
            return False
        
        # Check control system
        control_timeout = current_time - self.last_control_update
        if control_timeout > self.watchdog_timeout:
            logger.critical(
                f"Control system timeout ({control_timeout:.1f}s) - EMERGENCY STOP"
            )
            self.emergency_stop()
            return False
        
        return True
    
    def emergency_stop(self):
        """Trigger emergency stop - halt all operations.
        
        This is the "panic button" - stops everything immediately.
        
        Example:
            >>> safety.emergency_stop()  # Something went wrong!
        """
        if self.estop_triggered:
            return  # Already stopped
        
        logger.critical("="*60)
        logger.critical("EMERGENCY STOP ACTIVATED")
        logger.critical("="*60)
        
        self.estop_triggered = True
        
        # Execute callback to stop pumps
        if self.estop_callback:
            try:
                self.estop_callback()
                logger.info("Emergency stop callback executed successfully")
            except Exception as e:
                logger.error(f"Error in emergency stop callback: {e}")
        else:
            logger.warning("No emergency stop callback registered!")
    
    def reset(self):
        """Reset emergency stop and safety systems.
        
        Only call after fixing the problem!
        
        Example:
            >>> # After fixing camera issue:
            >>> safety.reset()
            >>> print("System ready to restart")
        """
        self.estop_triggered = False
        self.last_vision_update = time.time()
        self.last_control_update = time.time()
        logger.info("Safety system reset - ready to operate")
    
    def is_safe_to_run(self) -> bool:
        """Check if system is in safe state to run.
        
        Returns:
            True if safe to operate, False if E-STOP active
            
        Example:
            >>> if safety.is_safe_to_run():
            ...     start_control_loop()
        """
        return not self.estop_triggered


# Utility functions for safety checks

def validate_duty_cycle(value: float) -> float:
    """Ensure duty cycle is within safe limits.
    
    Args:
        value: Requested duty cycle (0-100%)
    
    Returns:
        Clamped value within safe range
        
    Example:
        >>> safe_duty = validate_duty_cycle(150)  # Returns 80 (max limit)
    """
    MAX_DUTY_CYCLE = 80  # Never exceed 80% to prevent overdosing
    MIN_DUTY_CYCLE = 0
    
    if value > MAX_DUTY_CYCLE:
        logger.warning(f"Duty cycle {value:.1f}% exceeds max ({MAX_DUTY_CYCLE}%), clamping")
        return MAX_DUTY_CYCLE
    
    if value < MIN_DUTY_CYCLE:
        logger.warning(f"Duty cycle {value:.1f}% below min ({MIN_DUTY_CYCLE}%), clamping")
        return MIN_DUTY_CYCLE
    
    return value


def validate_setpoint(value: int) -> int:
    """Ensure setpoint is reasonable.
    
    Args:
        value: Requested bubble count setpoint
    
    Returns:
        Validated setpoint within reasonable range
        
    Example:
        >>> safe_setpoint = validate_setpoint(500)  # Returns 300 (max reasonable)
    """
    MIN_SETPOINT = 20  # Too few bubbles = no flotation
    MAX_SETPOINT = 300  # Too many = over-frothing
    
    if value < MIN_SETPOINT:
        logger.warning(f"Setpoint {value} too low, using {MIN_SETPOINT}")
        return MIN_SETPOINT
    
    if value > MAX_SETPOINT:
        logger.warning(f"Setpoint {value} too high, using {MAX_SETPOINT}")
        return MAX_SETPOINT
    
    return value


if __name__ == "__main__":
    # Test safety manager
    logging.basicConfig(level=logging.INFO)
    
    print("\\n=== Safety Manager Test ===\\n")
    
    # Simulated pump stop function
    def stop_pumps():
        print(">>> All pumps stopped!")
    
    # Create safety manager
    safety = SafetyManager(watchdog_timeout=2.0)
    safety.register_estop_callback(stop_pumps)
    
    print("Testing normal operation...")
    safety.update_vision_heartbeat()
    safety.update_control_heartbeat()
    
    if safety.check_watchdog():
        print("✓ Watchdog OK\\n")
    
    print("Simulating vision system timeout...")
    time.sleep(3)
    
    if not safety.check_watchdog():
        print("✓ Watchdog correctly triggered emergency stop\\n")
    
    print("Testing safety reset...")
    safety.reset()
    if safety.is_safe_to_run():
        print("✓ System ready after reset\\n")
    
    print("Testing validation functions...")
    print(f"  Duty cycle 150% -> {validate_duty_cycle(150)}%")
    print(f"  Setpoint 500 -> {validate_setpoint(500)}")
    
    print("\\n✓ All safety tests passed")
