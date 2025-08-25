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
DOOR_OPEN_TIMEOUT = 30.0            # Max seconds door can stay open before auto-lock
SOLENOID_ACTIVE_LOW = True          # Solenoid relay is active low

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

# === SYSTEM INFORMATION ===
SYSTEM_VERSION = "1.0.0"
HARDWARE_VERSION = "RPi4"
SUPPORTED_PYTHON_VERSIONS = ["3.8", "3.9", "3.10", "3.11"]

# === GPIO VALIDATION ===
def validate_gpio_config():
    """Validate GPIO pin configuration for conflicts"""
    all_pins = []
    
    # Collect all used pins
    all_pins.extend(KEYPAD_ROWS)
    all_pins.extend(KEYPAD_COLS)
    all_pins.append(SOLENOID_LOCK_PIN)
    all_pins.append(DOOR_SENSOR_PIN)
    all_pins.extend(STATUS_LEDS.values())
    all_pins.append(BUZZER_PIN)
    
    # Check for duplicates
    if len(all_pins) != len(set(all_pins)):
        duplicates = [pin for pin in set(all_pins) if all_pins.count(pin) > 1]
        raise ValueError(f"Duplicate GPIO pins detected: {duplicates}")
    
    # Check for reserved pins (avoid power, ground, etc.)
    reserved_pins = [2, 3, 5, 6, 9, 14, 17, 20, 25, 30, 34, 39]  # Some reserved RPi pins
    conflicts = [pin for pin in all_pins if pin in reserved_pins]
    if conflicts:
        print(f"Warning: Using potentially reserved pins: {conflicts}")
    
    return True

# === HARDWARE TESTING FUNCTIONS ===
def get_pin_assignments():
    """Get dictionary of all pin assignments for documentation"""
    return {
        "keypad_rows": dict(zip(range(1, 5), KEYPAD_ROWS)),
        "keypad_cols": dict(zip(range(1, 5), KEYPAD_COLS)),
        "solenoid_lock": SOLENOID_LOCK_PIN,
        "door_sensor": DOOR_SENSOR_PIN,
        "status_leds": STATUS_LEDS,
        "buzzer": BUZZER_PIN
    }

def print_pin_configuration():
    """Print formatted pin configuration for documentation"""
    print("🔌 Smart Locker GPIO Pin Configuration")
    print("=" * 50)
    
    print("\n📟 Keypad Matrix (4x4):")
    for i, pin in enumerate(KEYPAD_ROWS, 1):
        print(f"  Row {i}: GPIO {pin}")
    for i, pin in enumerate(KEYPAD_COLS, 1):
        print(f"  Col {i}: GPIO {pin}")
    
    print(f"\n🔒 Lock Control:")
    print(f"  Solenoid: GPIO {SOLENOID_LOCK_PIN}")
    print(f"  Door Sensor: GPIO {DOOR_SENSOR_PIN}")
    
    print(f"\n💡 Status LEDs:")
    for color, pin in STATUS_LEDS.items():
        print(f"  {color.title()}: GPIO {pin}")
    
    print(f"\n🔊 Audio:")
    print(f"  Buzzer: GPIO {BUZZER_PIN}")
    
    print(f"\n⚙️ Timing Settings:")
    print(f"  Keypad debounce: {KEYPAD_DEBOUNCE_TIME}s")
    print(f"  Voice timeout: {VOICE_TIMEOUT}s")
    print(f"  PIN timeout: {PIN_INPUT_TIMEOUT}s")
    print(f"  Door unlock time: {LOCK_ENGAGEMENT_TIME}s")

# Validate configuration on import
if __name__ != "__main__":
    try:
        validate_gpio_config()
    except ValueError as e:
        print(f"⚠️  GPIO Configuration Error: {e}")

# CLI for testing configuration
if __name__ == "__main__":
    print_pin_configuration()
    print(f"\n✅ GPIO validation: {'Passed' if validate_gpio_config() else 'Failed'}")