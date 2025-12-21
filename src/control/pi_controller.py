"""
PI Controller for Froth Flotation

Simple, student-friendly PI control implementation.
Adjusts frother pump based on bubble count error.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class PIController:
    """PI (Proportional-Integral) controller for reagent dosing.
    
    Controls pump duty cycle based on difference between target and actual bubble count.
    """
    
    def __init__(self, kp: float = 0.5, ki: float = 0.05, setpoint: int = 120):
        """Initialize PI controller.
        
        Args:
            kp: Proportional gain (how strong the immediate response is)
            ki: Integral gain (how much we correct accumulated error)
            setpoint: Target bubble count we want to maintain
            
        Example:
            >>> controller = PIController(kp=0.5, ki=0.05, setpoint=120)
            >>> duty_cycle = controller.update(measured=100, dt=1.0)
        """
        self.kp = kp
        self.ki = ki
        self.setpoint = setpoint
        
        # Internal state
        self.integral = 0.0  # Sum of all past errors
        self.last_error = 0.0
        
        logger.info(f"PI Controller initialized: Kp={kp}, Ki={ki}, Setpoint={setpoint}")
    
    def update(self, measured_value: float, dt: float) -> float:
        """Calculate control output based on current measurement.
        
        This is the core PI algorithm:
        - Proportional: React to current error (how far from target)
        - Integral: React to accumulated error (persistent offset)
        
        Args:
            measured_value: Current bubble count from vision system
            dt: Time since last update (seconds)
        
        Returns:
            Pump duty cycle (0-100%) to apply
            
        Example:
            >>> # If we have 100 bubbles but want 120:
            >>> output = controller.update(measured=100, dt=1.0)
            >>> print(f"Increase pump to {output:.1f}%")
        """
        # Step 1: Calculate error (how far from target?)
        error = self.setpoint - measured_value
        
        # Step 2: Accumulate error over time (integral term)
        self.integral += error * dt
        
        # Anti-windup: Prevent integral from growing too large
        # This stops the controller from "overshooting" too much
        self.integral = np.clip(self.integral, -50, 50)
        
        # Step 3: Calculate control output
        # P term: React to current error
        # I term: Correct for persistent offset
        p_term = self.kp * error
        i_term = self.ki * self.integral
        output = p_term + i_term
        
        # Step 4: Limit output to valid pump range (0-100%)
        output = np.clip(output, 0, 100)
        
        # Save for next iteration
        self.last_error = error
        
        logger.debug(
            f"PI Update: error={error:.1f}, "
            f"P={p_term:.2f}, I={i_term:.2f}, output={output:.1f}%"
        )
        
        return output
    
    def reset(self):
        """Reset controller state (clear accumulated error).
        
        Use when switching modes or after stopping.
        
        Example:
            >>> controller.reset()  # Start fresh
        """
        self.integral = 0.0
        self.last_error = 0.0
        logger.info("PI Controller reset")
    
    def set_params(self, kp: float = None, ki: float = None, setpoint: int = None):
        """Update controller parameters on the fly.
        
        Args:
            kp: New proportional gain (or None to keep current)
            ki: New integral gain (or None to keep current)
            setpoint: New target value (or None to keep current)
            
        Example:
            >>> controller.set_params(kp=0.6, setpoint=150)
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if setpoint is not None:
            self.setpoint = setpoint
            
        logger.info(f"PI params updated: Kp={self.kp}, Ki={self.ki}, Setpoint={self.setpoint}")


# Tuning helper function
def estimate_gains(step_response_data: list, target_overshoot: float = 0.1) -> tuple:
    """Helper function to estimate PI gains from step response test.
    
    This is for advanced users doing manual tuning.
    
    Args:
        step_response_data: List of (time, bubble_count) tuples from step test
        target_overshoot: Desired overshoot fraction (0.1 = 10%)
    
    Returns:
        Tuple of (kp, ki) estimated gains
        
    Example:
        >>> # After running step test with constant pump duty cycle:
        >>> data = [(0, 100), (1, 110), (2, 118), (3, 120), ...]
        >>> kp, ki = estimate_gains(data)
        >>> print(f"Try Kp={kp:.2f}, Ki={ki:.3f}")
    """
    # Simple Ziegler-Nichols inspired estimation
    # This is a teaching tool - real tuning requires testing
    
    if len(step_response_data) < 3:
        logger.warning("Not enough data for gain estimation")
        return 0.5, 0.05
    
    # Extract times and values
    times = [t for t, _ in step_response_data]
    values = [v for _, v in step_response_data]
    
    # Find settling characteristics
    final_value = values[-1]
    initial_value = values[0]
    total_change = final_value - initial_value
    
    # Estimate time constant (time to reach 63% of final value)
    target_63 = initial_value + 0.63 * total_change
    tau = next((t for t, v in step_response_data if v >= target_63), times[-1])
    
    # Simple gain estimation
    kp = 0.9 / tau if tau > 0 else 0.5
    ki = kp / (3 * tau) if tau > 0 else 0.05
    
    logger.info(f"Estimated gains: Kp={kp:.3f}, Ki={ki:.3f} (tau={tau:.1f}s)")
    
    return kp, ki


if __name__ == "__main__":
    # Test the controller with simulated data
    logging.basicConfig(level=logging.INFO)
    
    print("\\n=== PI Controller Test ===\\n")
    
    # Create controller
    controller = PIController(kp=0.5, ki=0.05, setpoint=120)
    
    # Simulate system response
    measured = 80  # Start below setpoint
    dt = 1.0
    
    print(f"Target: {controller.setpoint} bubbles\\n")
    print(f"{'Step':<6} {'Measured':<10} {'Error':<8} {'Output':<8}")
    print("-" * 40)
    
    for step in range(20):
        # Calculate control output
        output = controller.update(measured, dt)
        error = controller.setpoint - measured
        
        print(f"{step:<6} {measured:<10.1f} {error:<8.1f} {output:<8.1f}%")
        
        # Simulate system response (simple first-order)
        # Real system would respond based on pump output
        measured += (output / 100) * 10 - 2  # Rough simulation
        measured = max(0, min(200, measured))  # Keep in bounds
    
    print("\\n✓ Test complete")
