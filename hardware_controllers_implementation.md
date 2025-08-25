# Hardware Controllers Implementation Plan

## 📡 Hardware Architecture Overview

```
Raspberry Pi 4 GPIO Layout for Smart Locker:

┌─── GPIO Pin Assignments ────┐
│                             │
│ KEYPAD 4x4 MATRIX:          │
│ ├── Rows: GPIO 18,19,20,21  │
│ └── Cols: GPIO 12,16,26,13  │
│                             │
│ LOCK CONTROL:               │
│ ├── Solenoid: GPIO 23       │
│ └── Door Sensor: GPIO 27    │
│                             │
│ STATUS INDICATORS:          │
│ ├── Red LED: GPIO 25        │
│ ├── Green LED: GPIO 24      │
│ ├── Blue LED: GPIO 22       │
│ └── Buzzer: GPIO 4          │
│                             │
│ AUDIO:                      │
│ ├── USB Microphone         │
│ └── 3.5mm Audio Out         │
└─────────────────────────────┘
```

## 🔧 Implementation Files

### 1. hardware/hardware_config.py

```python
# GPIO Pin Configuration for Smart Locker System
# Raspberry Pi 4 GPIO pin assignments

# === KEYPAD 4x4 MATRIX ===
KEYPAD_ROWS = [18, 19, 20, 21]        # GPIO pins for keypad rows (R1-R4)
KEYPAD_COLS = [12, 16, 26, 13]        # GPIO pins for keypad cols (C1-C4)

# Keypad layout mapping
KEYPAD_LAYOUT = [
    ['1', '2', '3', 'A'],    # Row 1: Numbers + Voice Recognition
    ['4', '5', '6', 'B'],    # Row 2: Numbers + Admin Mode
    ['7', '8', '9', 'C'],    # Row 3: Numbers + Status Check
    ['*', '0', '#', 'D']     # Row 4: Clear, Zero, Enter, Emergency
]

# Function key mappings
KEYPAD_FUNCTIONS = {
    'A': 'voice_recognition',     # Start voice recognition flow
    'B': 'admin_mode',           # Enter admin/setup mode
    'C': 'status_check',         # Check system status
    'D': 'emergency_unlock',     # Emergency override
    '*': 'clear_input',          # Clear current input
    '#': 'confirm_input'         # Confirm/Enter current input
}

# === LOCK CONTROL ===
SOLENOID_LOCK_PIN = 23              # Relay control for solenoid lock
DOOR_SENSOR_PIN = 27                # Magnetic sensor for door state
LOCK_ENGAGEMENT_TIME = 2.0          # Seconds to keep lock open
DOOR_TIMEOUT = 10.0                 # Max seconds door can stay open

# === STATUS INDICATORS ===
STATUS_LEDS = {
    'red': 25,      # Access denied / Error state
    'green': 24,    # Access granted / Ready state
    'blue': 22      # Processing / Working state
}

BUZZER_PIN = 4                      # Audio feedback buzzer

# === TIMING CONFIGURATIONS ===
KEYPAD_DEBOUNCE_TIME = 0.05         # Key debounce delay (seconds)
KEYPAD_SCAN_INTERVAL = 0.01         # How often to scan keypad
VOICE_TIMEOUT = 10.0                # Max voice recording time
PIN_INPUT_TIMEOUT = 30.0            # Max time to enter PIN
SYSTEM_READY_DELAY = 2.0            # Delay before system ready after boot

# === AUDIO SETTINGS ===
PREFERRED_SAMPLE_RATE = 16000       # Voice recording sample rate
AUDIO_BUFFER_SIZE = 1024            # Audio buffer size
MIC_DEVICE_NAME = "USB"             # Preferred microphone device substring

# === POWER MANAGEMENT ===
LOW_POWER_MODE_TIMEOUT = 300        # Enter low power after 5 minutes idle
LED_BRIGHTNESS = 0.5                # LED brightness (0.0-1.0)
BUZZER_VOLUME = 0.7                 # Buzzer volume (0.0-1.0)

# === SECURITY SETTINGS ===
MAX_CONSECUTIVE_FAILURES = 5       # Max failures before system lockdown
LOCKDOWN_DURATION = 900            # System lockdown time (15 minutes)
ADMIN_TIMEOUT = 120                # Admin mode timeout (2 minutes)
```

### 2. hardware/keypad_controller.py

```python
import RPi.GPIO as GPIO
import asyncio
import time
from typing import Optional, Callable
from .hardware_config import KEYPAD_ROWS, KEYPAD_COLS, KEYPAD_LAYOUT, KEYPAD_DEBOUNCE_TIME

class KeypadController:
    """
    4x4 Matrix Keypad Controller for Raspberry Pi GPIO
    Handles key scanning, debouncing, and event generation
    """
    
    def __init__(self):
        self.rows = KEYPAD_ROWS
        self.cols = KEYPAD_COLS
        self.layout = KEYPAD_LAYOUT
        self.debounce_time = KEYPAD_DEBOUNCE_TIME
        self.last_key_time = 0
        self.setup_gpio()
        
    def setup_gpio(self):
        """Initialize GPIO pins for keypad matrix"""
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
        for row_idx, row_pin in enumerate(self.rows):
            # Set current row LOW
            GPIO.output(row_pin, GPIO.LOW)
            
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
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_key = self.scan_keypad()
            if current_key != key:
                return True  # Key released
            
            await asyncio.sleep(0.01)
        
        return False  # Timeout
    
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()
    
    def __del__(self):
        """Destructor to ensure GPIO cleanup"""
        try:
            self.cleanup()
        except:
            pass
```

### 3. hardware/lock_controller.py

```python
import RPi.GPIO as GPIO
import asyncio
import time
from typing import Optional, Callable
from .hardware_config import SOLENOID_LOCK_PIN, DOOR_SENSOR_PIN, LOCK_ENGAGEMENT_TIME, DOOR_TIMEOUT

class LockController:
    """
    Electronic Lock Controller for Smart Locker
    Controls solenoid lock and monitors door sensor
    """
    
    def __init__(self, status_callback: Optional[Callable] = None):
        self.lock_pin = SOLENOID_LOCK_PIN
        self.door_pin = DOOR_SENSOR_PIN
        self.engagement_time = LOCK_ENGAGEMENT_TIME
        self.door_timeout = DOOR_TIMEOUT
        self.status_callback = status_callback
        self.is_locked = True
        self.door_open_time = None
        self.setup_gpio()
    
    def setup_gpio(self):
        """Initialize GPIO pins for lock control"""
        GPIO.setmode(GPIO.BCM)
        
        # Solenoid lock control (relay)
        GPIO.setup(self.lock_pin, GPIO.OUT)
        GPIO.output(self.lock_pin, GPIO.LOW)  # Initially locked
        
        # Door sensor (magnetic switch)
        GPIO.setup(self.door_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Set up door sensor interrupt
        GPIO.add_event_detect(self.door_pin, GPIO.BOTH, 
                            callback=self._door_sensor_callback, 
                            bouncetime=100)
    
    def _door_sensor_callback(self, channel):
        """GPIO interrupt callback for door sensor"""
        door_state = self.is_door_open()
        
        if door_state and self.door_open_time is None:
            # Door just opened
            self.door_open_time = time.time()
            if self.status_callback:
                self.status_callback("door_opened", {"timestamp": self.door_open_time})
        
        elif not door_state and self.door_open_time is not None:
            # Door just closed
            open_duration = time.time() - self.door_open_time
            self.door_open_time = None
            if self.status_callback:
                self.status_callback("door_closed", {"duration": open_duration})
    
    def is_door_open(self) -> bool:
        """
        Check if door is currently open
        
        Returns:
            True if door is open, False if closed
        """
        # LOW signal means door is open (magnetic contact broken)
        return GPIO.input(self.door_pin) == GPIO.LOW
    
    def is_door_locked(self) -> bool:
        """
        Check if lock is currently engaged
        
        Returns:
            True if locked, False if unlocked
        """
        return self.is_locked
    
    async def unlock_door(self, duration: Optional[float] = None) -> bool:
        """
        Unlock door for specified duration
        
        Args:
            duration: Time to keep door unlocked (seconds)
                     None for manual lock control
        
        Returns:
            Success boolean
        """
        try:
            # Activate solenoid (HIGH = unlock)
            GPIO.output(self.lock_pin, GPIO.HIGH)
            self.is_locked = False
            
            if self.status_callback:
                self.status_callback("lock_disengaged", {
                    "timestamp": time.time(),
                    "duration": duration
                })
            
            if duration:
                # Auto-lock after specified time
                await asyncio.sleep(duration)
                await self.lock_door()
            
            return True
            
        except Exception as e:
            if self.status_callback:
                self.status_callback("lock_error", {"error": str(e)})
            return False
    
    async def lock_door(self) -> bool:
        """
        Engage door lock
        
        Returns:
            Success boolean
        """
        try:
            # Deactivate solenoid (LOW = lock)
            GPIO.output(self.lock_pin, GPIO.LOW)
            self.is_locked = True
            
            if self.status_callback:
                self.status_callback("lock_engaged", {"timestamp": time.time()})
            
            return True
            
        except Exception as e:
            if self.status_callback:
                self.status_callback("lock_error", {"error": str(e)})
            return False
    
    async def emergency_unlock(self) -> bool:
        """
        Emergency unlock with extended duration
        
        Returns:
            Success boolean
        """
        if self.status_callback:
            self.status_callback("emergency_unlock", {"timestamp": time.time()})
        
        # Unlock for extended period during emergency
        return await self.unlock_door(duration=60.0)  # 1 minute emergency unlock
    
    def get_door_status(self) -> dict:
        """
        Get comprehensive door and lock status
        
        Returns:
            Status dictionary
        """
        door_open = self.is_door_open()
        lock_engaged = self.is_door_locked()
        
        status = {
            "door_open": door_open,
            "lock_engaged": lock_engaged,
            "timestamp": time.time()
        }
        
        if self.door_open_time:
            status["door_open_duration"] = time.time() - self.door_open_time
            status["door_timeout_remaining"] = max(0, self.door_timeout - status["door_open_duration"])
        
        return status
    
    async def monitor_door_timeout(self):
        """
        Monitor door timeout and auto-lock if door left open too long
        """
        while True:
            if self.door_open_time:
                open_duration = time.time() - self.door_open_time
                
                if open_duration > self.door_timeout:
                    # Door left open too long - force lock and alert
                    if self.status_callback:
                        self.status_callback("door_timeout", {
                            "duration": open_duration,
                            "action": "force_lock"
                        })
                    
                    await self.lock_door()
            
            await asyncio.sleep(1.0)  # Check every second
    
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.remove_event_detect(self.door_pin)
        GPIO.cleanup()
```

### 4. hardware/led_controller.py

```python
import RPi.GPIO as GPIO
import asyncio
import time
from typing import Dict, Optional, Tuple
from .hardware_config import STATUS_LEDS, LED_BRIGHTNESS

class LEDController:
    """
    RGB LED Status Indicator Controller
    Manages status LEDs for system state visualization
    """
    
    def __init__(self):
        self.led_pins = STATUS_LEDS
        self.brightness = LED_BRIGHTNESS
        self.current_state = "off"
        self.setup_gpio()
        
    def setup_gpio(self):
        """Initialize GPIO pins for LED control"""
        GPIO.setmode(GPIO.BCM)
        
        # Set up LED pins as PWM outputs for brightness control
        self.pwm_controllers = {}
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
        if color not in self.pwm_controllers:
            return
        
        if brightness is None:
            brightness = self.brightness
        
        # Convert brightness to duty cycle percentage
        duty_cycle = max(0, min(100, brightness * 100))
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
    
    def set_status(self, status: str):
        """
        Set LED status using predefined patterns
        
        Args:
            status: Status name (ready, processing, success, error, warning, off)
        """
        self.current_state = status
        
        status_patterns = {
            'ready': {'green': 1.0, 'red': 0, 'blue': 0},
            'processing': {'green': 0, 'red': 0, 'blue': 1.0},
            'success': {'green': 1.0, 'red': 0, 'blue': 0},
            'error': {'green': 0, 'red': 1.0, 'blue': 0},
            'warning': {'green': 0.5, 'red': 1.0, 'blue': 0},
            'admin': {'green': 0, 'red': 0.5, 'blue': 1.0},
            'off': {'green': 0, 'red': 0, 'blue': 0}
        }
        
        pattern = status_patterns.get(status, status_patterns['off'])
        self.set_rgb(**pattern)
    
    async def blink_status(self, status: str, duration: float = 2.0, blink_rate: float = 0.5):
        """
        Blink LED in specified status pattern
        
        Args:
            status: Status pattern to blink
            duration: Total blink duration (seconds)
            blink_rate: Blink rate (seconds per cycle)
        """
        start_time = time.time()
        
        while time.time() - start_time < duration:
            self.set_status(status)
            await asyncio.sleep(blink_rate / 2)
            self.set_status('off')
            await asyncio.sleep(blink_rate / 2)
        
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
        start_time = time.time()
        
        # Get status colors
        status_patterns = {
            'processing': {'green': 0, 'red': 0, 'blue': 1.0},
            'warning': {'green': 0.5, 'red': 1.0, 'blue': 0},
            'error': {'green': 0, 'red': 1.0, 'blue': 0}
        }
        
        colors = status_patterns.get(status, {'green': 0, 'red': 0, 'blue': 1.0})
        
        while time.time() - start_time < duration:
            # Calculate pulse brightness (sine wave)
            phase = (time.time() - start_time) * pulse_rate * 2 * 3.14159
            brightness = (math.sin(phase) + 1) / 2  # 0 to 1
            
            # Apply pulse to each color
            for color, base_level in colors.items():
                self.set_led(color, base_level * brightness)
            
            await asyncio.sleep(0.05)  # 20 FPS update rate
    
    async def startup_sequence(self):
        """LED startup sequence to indicate system boot"""
        # Test each LED
        for color in ['red', 'green', 'blue']:
            self.set_status('off')
            self.set_led(color, 1.0)
            await asyncio.sleep(0.5)
        
        # Flash all
        self.set_rgb(1.0, 1.0, 1.0)
        await asyncio.sleep(0.5)
        self.set_status('ready')
    
    def cleanup(self):
        """Clean up PWM and GPIO resources"""
        for pwm in self.pwm_controllers.values():
            pwm.stop()
        GPIO.cleanup()
```

### 5. hardware/buzzer_controller.py

```python
import RPi.GPIO as GPIO
import asyncio
import time
from typing import Optional
from .hardware_config import BUZZER_PIN, BUZZER_VOLUME

class BuzzerController:
    """
    Audio Buzzer Controller for Smart Locker
    Provides audio feedback for system events
    """
    
    def __init__(self):
        self.buzzer_pin = BUZZER_PIN
        self.volume = BUZZER_VOLUME
        self.setup_gpio()
    
    def setup_gpio(self):
        """Initialize GPIO pin for buzzer control"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.buzzer_pin, GPIO.OUT)
        
        # Set up PWM for tone generation
        self.pwm = GPIO.PWM(self.buzzer_pin, 1000)  # 1kHz default frequency
        self.pwm.start(0)  # Start with 0% duty cycle (off)
    
    def beep(self, frequency: int = 1000, duration: float = 0.1, volume: float = None):
        """
        Generate a beep tone
        
        Args:
            frequency: Tone frequency in Hz
            duration: Beep duration in seconds
            volume: Volume level (0.0-1.0), None for default
        """
        if volume is None:
            volume = self.volume
        
        # Set frequency and start tone
        self.pwm.ChangeFrequency(frequency)
        duty_cycle = volume * 50  # 50% max duty cycle for buzzer
        self.pwm.ChangeDutyCycle(duty_cycle)
        
        time.sleep(duration)
        
        # Stop tone
        self.pwm.ChangeDutyCycle(0)
    
    async def async_beep(self, frequency: int = 1000, duration: float = 0.1, volume: float = None):
        """Async version of beep"""
        if volume is None:
            volume = self.volume
        
        self.pwm.ChangeFrequency(frequency)
        duty_cycle = volume * 50
        self.pwm.ChangeDutyCycle(duty_cycle)
        
        await asyncio.sleep(duration)
        self.pwm.ChangeDutyCycle(0)
    
    async def success_sound(self):
        """Success sound pattern - ascending tones"""
        frequencies = [800, 1000, 1200]
        for freq in frequencies:
            await self.async_beep(freq, 0.15)
            await asyncio.sleep(0.05)
    
    async def error_sound(self):
        """Error sound pattern - descending tones"""
        frequencies = [1200, 1000, 800]
        for freq in frequencies:
            await self.async_beep(freq, 0.2)
            await asyncio.sleep(0.1)
    
    async def warning_sound(self):
        """Warning sound pattern - alternating tones"""
        for _ in range(3):
            await self.async_beep(800, 0.1)
            await asyncio.sleep(0.1)
            await self.async_beep(1200, 0.1)
            await asyncio.sleep(0.1)
    
    async def processing_sound(self):
        """Processing sound - single short beep"""
        await self.async_beep(1000, 0.05)
    
    async def keypress_sound(self):
        """Keypress feedback - very short beep"""
        await self.async_beep(1500, 0.03, 0.3)
    
    async def startup_sound(self):
        """System startup sound sequence"""
        # Rising tone sweep
        for freq in range(400, 1601, 100):
            await self.async_beep(freq, 0.05)
        
        await asyncio.sleep(0.2)
        
        # Confirmation beeps
        for _ in range(2):
            await self.async_beep(1200, 0.1)
            await asyncio.sleep(0.1)
    
    async def alarm_sound(self, duration: float = 5.0):
        """Alarm sound for security alerts"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            await self.async_beep(2000, 0.5, 0.8)
            await asyncio.sleep(0.1)
            await self.async_beep(1500, 0.5, 0.8)
            await asyncio.sleep(0.1)
    
    def cleanup(self):
        """Clean up PWM and GPIO resources"""
        self.pwm.stop()
        GPIO.cleanup()
```

## 🔌 Integration Requirements

### Dependencies to Add

```bash
# Add to requirements_rpi.txt
RPi.GPIO>=0.7.0
gpiozero>=1.6.0  # Alternative GPIO library
```

### System Setup Commands

```bash
# Enable GPIO access for pi user
sudo usermod -a -G gpio pi

# Install BCM2835 library (if needed)
sudo apt-get install -y python3-rpi.gpio

# Enable SPI and I2C (if using additional sensors)
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
```

## 🔧 Usage Integration

### Main Controller Integration

```python
from hardware import KeypadController, LockController, LEDController, BuzzerController

class SmartLockerController:
    def __init__(self):
        self.keypad = KeypadController()
        self.lock = LockController(status_callback=self.hardware_status_callback)
        self.leds = LEDController()
        self.buzzer = BuzzerController()
        
    async def hardware_status_callback(self, event: str, data: dict):
        """Handle hardware events"""
        if event == "door_opened":
            await self.buzzer.success_sound()
            self.leds.set_status('success')
        elif event == "door_timeout":
            await self.buzzer.alarm_sound(2.0)
            self.leds.set_status('error')
```

This hardware implementation provides complete GPIO control for the smart locker system with proper error handling, async support, and comprehensive status feedback.