"""
Pump Driver for Flotation Control System
Raspberry Pi 5 - lgpio Compatible

Provides PWM control for:
- Frother pump (GPIO 12)
- Agitator (GPIO 13)
- Air pump (GPIO 14)
- Feed pump (GPIO 15)
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Import lgpio for Raspberry Pi 5
try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.error("lgpio not available! Install with: sudo apt install python3-lgpio")


class PumpDriver:
    """
    Hardware abstraction layer for pump control using lgpio (Raspberry Pi 5)
    """
    
    # GPIO Pin Assignments (from config)
    FROTHER_PUMP_PIN = 12  # Hardware PWM0
    AGITATOR_PIN = 13     # Hardware PWM1
    AIR_PUMP_PIN = 14      # Software PWM
    FEED_PUMP_PIN = 15     # Software PWM
    
    PWM_FREQUENCY = 1000   # 1kHz PWM frequency
    
    def __init__(self):
        """Initialize pump driver with lgpio."""
        if not GPIO_AVAILABLE:
            raise RuntimeError(
                "lgpio library not available. "
                "Install with: sudo apt install python3-lgpio"
            )
        
        self.chip = None
        self._init_lgpio()
    
    def _init_lgpio(self):
        """Initialize lgpio for Raspberry Pi 5."""
        try:
            # Open GPIO chip 0 (Raspberry Pi 5)
            self.chip = lgpio.gpiochip_open(0)
            logger.info("lgpio chip opened successfully")
            
            # Claim all GPIO pins as outputs
            all_pins = [
                self.FROTHER_PUMP_PIN,
                self.AGITATOR_PIN,
                self.AIR_PUMP_PIN,
                self.FEED_PUMP_PIN
            ]
            
            for pin in all_pins:
                # Claim pin as output
                lgpio.gpio_claim_output(self.chip, int(pin))
                # Initialize PWM at 0% duty cycle (all args must be int)
                lgpio.tx_pwm(self.chip, int(pin), int(self.PWM_FREQUENCY), 0)
                logger.debug(f"Initialized GPIO {pin} for PWM control")
            
            logger.info("All pump pins initialized successfully (lgpio)")
            
        except Exception as e:
            logger.error(f"Failed to initialize lgpio: {e}")
            if self.chip is not None:
                lgpio.gpiochip_close(self.chip)
            raise RuntimeError(f"lgpio initialization failed: {e}")
    
    def set_duty_cycle(self, pin: int, duty_cycle: float):
        """
        Set PWM duty cycle for a specific GPIO pin.
        
        Args:
            pin: GPIO pin number (12, 13, 14, or 15)
            duty_cycle: 0-100 (percentage)
        """
        if self.chip is None:
            logger.error("GPIO chip not initialized")
            return
        
        # Clamp duty cycle to valid range
        duty_cycle = max(0.0, min(100.0, duty_cycle))
        
        try:
            # lgpio.tx_pwm requires ALL arguments to be integers
            # Args: (handle, gpio_pin, frequency, duty_cycle)
            lgpio.tx_pwm(self.chip, int(pin), int(self.PWM_FREQUENCY), int(round(duty_cycle)))
            logger.debug(f"GPIO {pin} set to {int(round(duty_cycle))}% duty cycle")
            
        except Exception as e:
            logger.error(f"Failed to set duty cycle on GPIO {pin}: {e}")
    
    def set_frother_pump(self, duty_cycle: float):
        """
        Set frother pump speed.
        
        Args:
            duty_cycle: 0-100 (percentage), controls reagent dosing rate
        """
        self.set_duty_cycle(self.FROTHER_PUMP_PIN, duty_cycle)
        logger.info(f"Frother pump set to {duty_cycle:.1f}%")
    
    def set_agitator(self, duty_cycle: float):
        """
        Set agitator motor speed.
        
        Args:
            duty_cycle: 0-100 (percentage), controls mixing intensity
        """
        self.set_duty_cycle(self.AGITATOR_PIN, duty_cycle)
        logger.info(f"Agitator set to {duty_cycle:.1f}%")
    
    def set_air_pump(self, duty_cycle: float):
        """
        Set air pump speed.
        
        Args:
            duty_cycle: 0-100 (percentage), controls air flow rate
        """
        self.set_duty_cycle(self.AIR_PUMP_PIN, duty_cycle)
        logger.info(f"Air pump set to {duty_cycle:.1f}%")
    
    def set_feed_pump(self, duty_cycle: float):
        """
        Set feed pump speed.
        
        Args:
            duty_cycle: 0-100 (percentage), controls slurry feed rate
        """
        self.set_duty_cycle(self.FEED_PUMP_PIN, duty_cycle)
        logger.info(f"Feed pump set to {duty_cycle:.1f}%")
    
    def stop_all(self):
        """Emergency stop - set all pumps to 0%."""
        logger.warning("EMERGENCY STOP - All pumps halted")
        
        for pin in [self.FROTHER_PUMP_PIN, self.AGITATOR_PIN, 
                   self.AIR_PUMP_PIN, self.FEED_PUMP_PIN]:
            self.set_duty_cycle(pin, 0)
    
    def get_status(self) -> dict:
        """
        Get current status of all pumps.
        
        Returns:
            Dictionary with pump names and current states
        """
        return {
            'gpio_library': 'lgpio',
            'chip_open': self.chip is not None,
            'frother_pin': self.FROTHER_PUMP_PIN,
            'agitator_pin': self.AGITATOR_PIN,
            'air_pump_pin': self.AIR_PUMP_PIN,
            'feed_pump_pin': self.FEED_PUMP_PIN,
            'pwm_frequency': self.PWM_FREQUENCY
        }
    
    def cleanup(self):
        """Clean up GPIO resources."""
        logger.info("Cleaning up GPIO resources")
        
        # Stop all pumps
        self.stop_all()
        
        # Close GPIO chip
        if self.chip is not None:
            try:
                lgpio.gpiochip_close(self.chip)
                logger.info("GPIO chip closed successfully")
            except Exception as e:
                logger.error(f"Error closing GPIO chip: {e}")
            finally:
                self.chip = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Test script
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 50)
    print("Pump Driver Test - Raspberry Pi 5 (lgpio)")
    print("=" * 50)
    
    if not GPIO_AVAILABLE:
        print("\n✗ ERROR: lgpio not available!")
        print("Install with: sudo apt install python3-lgpio")
        exit(1)
    
    try:
        with PumpDriver() as driver:
            print("\n✓ Pump driver initialized successfully")
            
            # Show status
            status = driver.get_status()
            print(f"\nDriver Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            # Test each pump
            pumps = [
                (driver.FROTHER_PUMP_PIN, "Frother Pump", driver.set_frother_pump),
                (driver.AGITATOR_PIN, "Agitator", driver.set_agitator),
                (driver.AIR_PUMP_PIN, "Air Pump", driver.set_air_pump),
                (driver.FEED_PUMP_PIN, "Feed Pump", driver.set_feed_pump)
            ]
            
            print("\n" + "=" * 50)
            print("Testing PWM Control")
            print("=" * 50)
            
            for pin, name, set_func in pumps:
                print(f"\nTesting {name} (GPIO {pin})...")
                for duty in [0, 25, 50, 75, 100]:
                    set_func(duty)
                    print(f"  ├─ {duty}% duty cycle")
                    time.sleep(0.3)
                set_func(0)
                print(f"  └─ Stopped")
            
            print("\n" + "=" * 50)
            print("✓ All pumps tested successfully!")
            print("=" * 50)
            
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
