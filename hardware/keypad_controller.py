import asyncio
import time
from typing import Optional, Callable
from .hardware_config import KEYPAD_ROWS, KEYPAD_COLS, KEYPAD_LAYOUT, KEYPAD_DEBOUNCE_TIME

# Try to import RPi.GPIO, fallback to simulation mode if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - running in simulation mode")

class KeypadController:
    """
    4x4 Matrix Keypad Controller for Raspberry Pi GPIO
    Handles key scanning, debouncing, and event generation
    Supports simulation mode when RPi.GPIO is not available
    """
    
    def __init__(self, simulation_mode=None):
        self.rows = KEYPAD_ROWS
        self.cols = KEYPAD_COLS
        self.layout = KEYPAD_LAYOUT
        self.debounce_time = KEYPAD_DEBOUNCE_TIME
        self.last_key_time = 0
        
        # Determine if we should use simulation mode
        if simulation_mode is None:
            self.simulation_mode = not GPIO_AVAILABLE
        else:
            self.simulation_mode = simulation_mode
        
        if not self.simulation_mode:
            self.setup_gpio()
        else:
            print("🔧 Keypad running in simulation mode")
    
    def setup_gpio(self):
        """Initialize GPIO pins for keypad matrix"""
        if self.simulation_mode:
            return
        
        GPIO.setmode(GPIO.BCM)
        
        # Set up row pins as outputs (initially HIGH)
        for row_pin in self.rows:
            GPIO.setup(row_pin, GPIO.OUT)
            GPIO.output(row_pin, GPIO.HIGH)
        
        # Set up column pins as inputs with pull-up resistors
        for col_pin in self.cols:
            GPIO.setup(col_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def scan_keypad(self) -> Optional[str]:
        """
        Scan keypad matrix for pressed keys
        
        Returns:
            Key character if pressed, None if no key pressed
        """
        if self.simulation_mode:
            return None  # No simulation for scanning
        
        for row_idx, row_pin in enumerate(self.rows):
            # Set current row LOW
            GPIO.output(row_pin, GPIO.LOW)
            
            # Small delay for signal to stabilize
            time.sleep(0.001)
            
            # Check each column
            for col_idx, col_pin in enumerate(self.cols):
                if GPIO.input(col_pin) == GPIO.LOW:
                    # Key press detected
                    key = self.layout[row_idx][col_idx]
                    
                    # Reset row pin to HIGH
                    GPIO.output(row_pin, GPIO.HIGH)
                    
                    # Debounce check
                    current_time = time.time()
                    if current_time - self.last_key_time > self.debounce_time:
                        self.last_key_time = current_time
                        return key
                    
                    return None  # Too soon since last key press
            
            # Reset row pin to HIGH
            GPIO.output(row_pin, GPIO.HIGH)
        
        return None
    
    async def wait_for_key(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Wait for a key press with optional timeout
        
        Args:
            timeout: Maximum time to wait in seconds (None for infinite)
            
        Returns:
            Pressed key character or None if timeout
        """
        if self.simulation_mode:
            # Simulation mode - return None after timeout
            if timeout:
                await asyncio.sleep(timeout)
            else:
                await asyncio.sleep(1.0)
            return None
        
        start_time = time.time()
        
        while True:
            # Check for timeout
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            # Scan for key press
            key = self.scan_keypad()
            if key:
                return key
            
            # Small delay to prevent excessive CPU usage
            await asyncio.sleep(0.01)
    
    async def wait_for_key_release(self, key: str, timeout: float = 1.0) -> bool:
        """
        Wait for a specific key to be released
        
        Args:
            key: Key character to wait for release
            timeout: Maximum time to wait
            
        Returns:
            True if key was released, False if timeout
        """
        if self.simulation_mode:
            await asyncio.sleep(0.1)  # Simulate key release
            return True
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_key = self.scan_keypad()
            if current_key != key:
                return True  # Key released
            
            await asyncio.sleep(0.01)
        
        return False  # Timeout
    
    def get_key_position(self, key: str) -> tuple:
        """
        Get row, column position of a key
        
        Args:
            key: Key character
            
        Returns:
            Tuple of (row, col) or None if key not found
        """
        for row_idx, row in enumerate(self.layout):
            for col_idx, k in enumerate(row):
                if k == key:
                    return (row_idx, col_idx)
        return None
    
    def is_function_key(self, key: str) -> bool:
        """Check if key is a function key (A, B, C, D)"""
        return key in ['A', 'B', 'C', 'D']
    
    def is_numeric_key(self, key: str) -> bool:
        """Check if key is numeric (0-9)"""
        return key.isdigit()
    
    def is_control_key(self, key: str) -> bool:
        """Check if key is a control key (*, #)"""
        return key in ['*', '#']
    
    def get_key_description(self, key: str) -> str:
        """Get human-readable description of key function"""
        descriptions = {
            'A': 'Voice Recognition',
            'B': 'Admin Mode',
            'C': 'Status Check',
            'D': 'Emergency Unlock',
            '*': 'Clear',
            '#': 'Enter/Confirm',
            '0': 'Zero',
            '1': 'One', '2': 'Two', '3': 'Three',
            '4': 'Four', '5': 'Five', '6': 'Six',
            '7': 'Seven', '8': 'Eight', '9': 'Nine'
        }
        return descriptions.get(key, f"Key {key}")
    
    async def test_all_keys(self, callback: Optional[Callable] = None) -> dict:
        """
        Test all keys on the keypad
        
        Args:
            callback: Optional callback function for each key press
            
        Returns:
            Dictionary with test results
        """
        if self.simulation_mode:
            print("🔧 Keypad test running in simulation mode")
            # Simulate all keys working
            results = {}
            for row in self.layout:
                for key in row:
                    results[key] = True
                    if callback:
                        callback(f"Simulated key press: {key}")
                    await asyncio.sleep(0.1)
            return results
        
        print("🧪 Testing keypad - press each key when prompted...")
        results = {}
        
        for row in self.layout:
            for key in row:
                print(f"Press key '{key}' ({self.get_key_description(key)})...")
                
                # Wait for the specific key to be pressed
                start_time = time.time()
                timeout = 10.0  # 10 second timeout per key
                
                while time.time() - start_time < timeout:
                    pressed_key = self.scan_keypad()
                    if pressed_key == key:
                        results[key] = True
                        if callback:
                            callback(f"✅ Key {key} working")
                        print(f"✅ Key {key} detected")
                        
                        # Wait for release
                        await self.wait_for_key_release(key)
                        break
                    elif pressed_key:
                        if callback:
                            callback(f"⚠️  Expected {key}, got {pressed_key}")
                        print(f"⚠️  Expected {key}, got {pressed_key}")
                    
                    await asyncio.sleep(0.05)
                else:
                    # Timeout
                    results[key] = False
                    if callback:
                        callback(f"❌ Key {key} timeout")
                    print(f"❌ Key {key} timeout")
        
        return results
    
    def get_keypad_layout_string(self) -> str:
        """Get formatted string representation of keypad layout"""
        layout_str = "┌─────────────────┐\n"
        layout_str += "│  KEYPAD LAYOUT  │\n"
        layout_str += "├─────────────────┤\n"
        
        for row in self.layout:
            layout_str += "│ "
            for key in row:
                layout_str += f"[{key}] "
            layout_str += "│\n"
        
        layout_str += "└─────────────────┘\n"
        layout_str += "\nFunctions:\n"
        layout_str += "A: Voice Recognition\n"
        layout_str += "B: Admin Mode\n"
        layout_str += "C: Status Check\n"
        layout_str += "D: Emergency Unlock\n"
        layout_str += "*: Clear Input\n"
        layout_str += "#: Enter/Confirm\n"
        
        return layout_str
    
    def cleanup(self):
        """Clean up GPIO resources"""
        if not self.simulation_mode and GPIO_AVAILABLE:
            try:
                # Reset all pins to inputs
                for pin in self.rows + self.cols:
                    GPIO.setup(pin, GPIO.IN)
                GPIO.cleanup()
            except Exception as e:
                print(f"⚠️  GPIO cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure GPIO cleanup"""
        try:
            self.cleanup()
        except:
            pass

# Testing and simulation functions
async def simulate_key_presses(keypad: KeypadController, keys: list, delay: float = 0.5):
    """
    Simulate a sequence of key presses for testing
    
    Args:
        keypad: KeypadController instance
        keys: List of keys to simulate
        delay: Delay between key presses
    """
    print(f"🎮 Simulating key sequence: {' -> '.join(keys)}")
    
    for key in keys:
        print(f"Simulating key press: {key}")
        # In a real simulation, we would inject the key into the controller
        await asyncio.sleep(delay)

# CLI testing interface
async def main():
    """CLI interface for keypad testing"""
    print("🔢 Keypad Controller Test")
    print("=" * 30)
    
    keypad = KeypadController()
    
    try:
        print(keypad.get_keypad_layout_string())
        
        if keypad.simulation_mode:
            print("Running in simulation mode")
            # Test simulation
            await simulate_key_presses(keypad, ['A', '1', '2', '3', '4', '#'])
        else:
            print("Press keys to test (Ctrl+C to exit)")
            while True:
                key = await keypad.wait_for_key(timeout=1.0)
                if key:
                    description = keypad.get_key_description(key)
                    print(f"Key pressed: {key} ({description})")
    
    except KeyboardInterrupt:
        print("\n👋 Keypad test stopped")
    finally:
        keypad.cleanup()

if __name__ == "__main__":
    asyncio.run(main())