import asyncio
import time
import math
from typing import Dict, Optional, Tuple
from .hardware_config import STATUS_LEDS, LED_BRIGHTNESS

# Try to import RPi.GPIO, fallback to simulation mode if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - LED controller running in simulation mode")

class LEDController:
    """
    RGB LED Status Indicator Controller
    Manages status LEDs for system state visualization
    Supports simulation mode when RPi.GPIO is not available
    """
    
    def __init__(self, simulation_mode=None):
        self.led_pins = STATUS_LEDS
        self.brightness = LED_BRIGHTNESS
        self.current_state = "off"
        self.pwm_controllers = {}
        
        # Determine if we should use simulation mode
        if simulation_mode is None:
            self.simulation_mode = not GPIO_AVAILABLE
        else:
            self.simulation_mode = simulation_mode
        
        if not self.simulation_mode:
            self.setup_gpio()
        else:
            print("🔧 LED controller running in simulation mode")
    
    def setup_gpio(self):
        """Initialize GPIO pins for LED control"""
        if self.simulation_mode:
            return
        
        GPIO.setmode(GPIO.BCM)
        
        # Set up LED pins as PWM outputs for brightness control
        for color, pin in self.led_pins.items():
            GPIO.setup(pin, GPIO.OUT)
            pwm = GPIO.PWM(pin, 1000)  # 1kHz frequency
            pwm.start(0)  # Start with 0% duty cycle (off)
            self.pwm_controllers[color] = pwm
    
    def set_led(self, color: str, brightness: float = None):
        """
        Set individual LED brightness
        
        Args:
            color: LED color ('red', 'green', 'blue')
            brightness: Brightness level (0.0-1.0), None to use default
        """
        if color not in self.led_pins:
            print(f"⚠️  Unknown LED color: {color}")
            return
        
        if brightness is None:
            brightness = self.brightness
        
        # Clamp brightness to valid range
        brightness = max(0.0, min(1.0, brightness))
        
        if self.simulation_mode:
            # Simulation mode - just print the action
            status = "ON" if brightness > 0 else "OFF"
            if brightness > 0:
                print(f"💡 LED {color.upper()}: {status} ({brightness:.1%} brightness)")
            return
        
        # Convert brightness to duty cycle percentage
        duty_cycle = brightness * 100
        self.pwm_controllers[color].ChangeDutyCycle(duty_cycle)
    
    def set_rgb(self, red: float = 0, green: float = 0, blue: float = 0):
        """
        Set RGB values simultaneously
        
        Args:
            red: Red brightness (0.0-1.0)
            green: Green brightness (0.0-1.0)
            blue: Blue brightness (0.0-1.0)
        """
        self.set_led('red', red)
        self.set_led('green', green)
        self.set_led('blue', blue)
        
        if self.simulation_mode and (red > 0 or green > 0 or blue > 0):
            print(f"🌈 RGB: R={red:.1%}, G={green:.1%}, B={blue:.1%}")
    
    def set_status(self, status: str, brightness: float = None):
        """
        Set LED status using predefined patterns
        
        Args:
            status: Status name (ready, processing, success, error, warning, admin, off)
            brightness: Override default brightness
        """
        self.current_state = status
        
        status_patterns = {
            'ready': {'red': 0, 'green': 1.0, 'blue': 0},           # Green
            'processing': {'red': 0, 'green': 0, 'blue': 1.0},      # Blue
            'success': {'red': 0, 'green': 1.0, 'blue': 0},         # Green
            'error': {'red': 1.0, 'green': 0, 'blue': 0},           # Red
            'warning': {'red': 1.0, 'green': 0.5, 'blue': 0},       # Orange
            'admin': {'red': 0.5, 'green': 0, 'blue': 1.0},         # Purple
            'emergency': {'red': 1.0, 'green': 0, 'blue': 0},       # Red
            'locked': {'red': 0.3, 'green': 0, 'blue': 0},          # Dim Red
            'off': {'red': 0, 'green': 0, 'blue': 0}                # Off
        }
        
        pattern = status_patterns.get(status, status_patterns['off'])
        
        # Apply brightness override if specified
        if brightness is not None:
            pattern = {color: value * brightness for color, value in pattern.items()}
        
        self.set_rgb(**pattern)
        
        if self.simulation_mode:
            print(f"🎯 Status: {status.upper()}")
    
    async def blink_status(self, status: str, duration: float = 2.0, blink_rate: float = 0.5, cycles: int = None):
        """
        Blink LED in specified status pattern
        
        Args:
            status: Status pattern to blink
            duration: Total blink duration (seconds)
            blink_rate: Blink rate (seconds per cycle)
            cycles: Number of blink cycles (overrides duration if specified)
        """
        if self.simulation_mode:
            cycle_count = cycles if cycles else int(duration / blink_rate)
            print(f"⚡ Blinking {status} for {cycle_count} cycles")
            await asyncio.sleep(duration if not cycles else cycles * blink_rate)
            return
        
        start_time = time.time()
        cycle_count = 0
        
        while True:
            # Check termination conditions
            if cycles and cycle_count >= cycles:
                break
            if not cycles and (time.time() - start_time) >= duration:
                break
            
            # On phase
            self.set_status(status)
            await asyncio.sleep(blink_rate / 2)
            
            # Off phase
            self.set_status('off')
            await asyncio.sleep(blink_rate / 2)
            
            cycle_count += 1
        
        # Restore previous state
        self.set_status(self.current_state)
    
    async def pulse_status(self, status: str, duration: float = 2.0, pulse_rate: float = 1.0):
        """
        Pulse LED brightness for specified status
        
        Args:
            status: Status pattern to pulse
            duration: Total pulse duration (seconds)
            pulse_rate: Pulses per second
        """
        if self.simulation_mode:
            print(f"🌊 Pulsing {status} for {duration}s at {pulse_rate}Hz")
            await asyncio.sleep(duration)
            return
        
        # Get status colors
        status_patterns = {
            'processing': {'red': 0, 'green': 0, 'blue': 1.0},
            'warning': {'red': 1.0, 'green': 0.5, 'blue': 0},
            'error': {'red': 1.0, 'green': 0, 'blue': 0},
            'ready': {'red': 0, 'green': 1.0, 'blue': 0}
        }
        
        colors = status_patterns.get(status, {'red': 0, 'green': 0, 'blue': 1.0})
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Calculate pulse brightness (sine wave)
            phase = (time.time() - start_time) * pulse_rate * 2 * math.pi
            brightness = (math.sin(phase) + 1) / 2  # 0 to 1
            
            # Apply pulse to each color
            for color, base_level in colors.items():
                self.set_led(color, base_level * brightness)
            
            await asyncio.sleep(0.05)  # 20 FPS update rate
        
        # Restore to current status
        self.set_status(self.current_state)
    
    async def fade_transition(self, from_status: str, to_status: str, duration: float = 1.0):
        """
        Fade transition between two status patterns
        
        Args:
            from_status: Starting status
            to_status: Ending status
            duration: Transition duration (seconds)
        """
        if self.simulation_mode:
            print(f"🌅 Fading from {from_status} to {to_status} over {duration}s")
            await asyncio.sleep(duration)
            self.set_status(to_status)
            return
        
        # Get color patterns
        status_patterns = {
            'ready': {'red': 0, 'green': 1.0, 'blue': 0},
            'processing': {'red': 0, 'green': 0, 'blue': 1.0},
            'success': {'red': 0, 'green': 1.0, 'blue': 0},
            'error': {'red': 1.0, 'green': 0, 'blue': 0},
            'warning': {'red': 1.0, 'green': 0.5, 'blue': 0},
            'admin': {'red': 0.5, 'green': 0, 'blue': 1.0},
            'off': {'red': 0, 'green': 0, 'blue': 0}
        }
        
        from_colors = status_patterns.get(from_status, status_patterns['off'])
        to_colors = status_patterns.get(to_status, status_patterns['off'])
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Calculate interpolation factor (0 to 1)
            progress = (time.time() - start_time) / duration
            progress = max(0, min(1, progress))  # Clamp to [0,1]
            
            # Interpolate each color
            interpolated = {}
            for color in ['red', 'green', 'blue']:
                from_val = from_colors.get(color, 0)
                to_val = to_colors.get(color, 0)
                interpolated[color] = from_val + (to_val - from_val) * progress
            
            self.set_rgb(**interpolated)
            await asyncio.sleep(0.02)  # 50 FPS update rate
        
        # Ensure final state
        self.set_status(to_status)
    
    async def startup_sequence(self):
        """LED startup sequence to indicate system boot"""
        if self.simulation_mode:
            print("🚀 LED startup sequence (simulation)")
            await asyncio.sleep(2.0)
            self.set_status('ready')
            return
        
        # Test each LED
        for color in ['red', 'green', 'blue']:
            self.set_status('off')
            self.set_led(color, 1.0)
            await asyncio.sleep(0.5)
        
        # Flash all colors
        self.set_rgb(1.0, 1.0, 1.0)
        await asyncio.sleep(0.5)
        
        # Fade to ready
        await self.fade_transition('off', 'ready', 1.0)
    
    async def alarm_sequence(self, duration: float = 5.0):
        """Emergency alarm LED sequence"""
        if self.simulation_mode:
            print(f"🚨 ALARM sequence for {duration}s (simulation)")
            await asyncio.sleep(duration)
            return
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Fast red blink
            self.set_status('error')
            await asyncio.sleep(0.2)
            self.set_status('off')
            await asyncio.sleep(0.2)
    
    def get_current_status(self) -> dict:
        """Get current LED status"""
        if self.simulation_mode:
            return {
                "simulation_mode": True,
                "current_state": self.current_state,
                "brightness": self.brightness
            }
        
        # In real mode, we can't read PWM values, so return state
        return {
            "simulation_mode": False,
            "current_state": self.current_state,
            "brightness": self.brightness,
            "pins": self.led_pins
        }
    
    async def test_all_colors(self):
        """Test all LED colors sequentially"""
        print("🧪 Testing all LED colors...")
        
        test_sequence = [
            ('red', 'Red - Error/Denied'),
            ('green', 'Green - Success/Ready'),
            ('blue', 'Blue - Processing'),
            ('warning', 'Orange - Warning'),
            ('admin', 'Purple - Admin Mode'),
            ('off', 'Off - All LEDs off')
        ]
        
        for status, description in test_sequence:
            print(f"Testing: {description}")
            if status in ['red', 'green', 'blue']:
                self.set_led(status, 1.0)
            else:
                self.set_status(status)
            await asyncio.sleep(2.0)
        
        print("✅ LED color test completed")
    
    def cleanup(self):
        """Clean up PWM and GPIO resources"""
        if not self.simulation_mode and GPIO_AVAILABLE:
            try:
                # Stop all PWM controllers
                for pwm in self.pwm_controllers.values():
                    pwm.stop()
                
                # Reset GPIO pins
                for pin in self.led_pins.values():
                    GPIO.setup(pin, GPIO.IN)
                
                GPIO.cleanup()
            except Exception as e:
                print(f"⚠️  LED GPIO cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass

# CLI testing interface
async def main():
    """CLI interface for LED testing"""
    print("💡 LED Controller Test")
    print("=" * 25)
    
    led_controller = LEDController()
    
    try:
        # Startup sequence
        await led_controller.startup_sequence()
        await asyncio.sleep(1)
        
        # Test all colors
        await led_controller.test_all_colors()
        await asyncio.sleep(1)
        
        # Test blink
        print("Testing blink patterns...")
        await led_controller.blink_status('error', duration=3.0)
        await asyncio.sleep(1)
        
        # Test pulse
        print("Testing pulse pattern...")
        await led_controller.pulse_status('processing', duration=3.0)
        await asyncio.sleep(1)
        
        # Test fade transition
        print("Testing fade transition...")
        await led_controller.fade_transition('error', 'success', duration=2.0)
        await asyncio.sleep(1)
        
        # Final status
        led_controller.set_status('ready')
        print("✅ LED test completed - ready status")
        
    except KeyboardInterrupt:
        print("\n👋 LED test stopped")
    finally:
        led_controller.cleanup()

if __name__ == "__main__":
    asyncio.run(main())