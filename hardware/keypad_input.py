import asyncio
import time
from typing import Optional, Callable, List
from datetime import datetime
from .keypad_controller import KeypadController
from .led_controller import LEDController
from .buzzer_controller import BuzzerController
from .lock_controller import LockController

class KeypadInputHandler:
    """
    Unified Keypad Input Handler for Smart Locker
    Manages keypad input with visual and audio feedback
    Handles PIN entry, emergency codes, and system commands
    """
    
    def __init__(self, 
                 keypad: KeypadController,
                 led: LEDController, 
                 buzzer: BuzzerController,
                 lock: LockController):
        self.keypad = keypad
        self.led = led
        self.buzzer = buzzer
        self.lock = lock
        
        # Input state
        self.current_input = ""
        self.input_mode = "normal"  # normal, emergency, admin, voice_trigger
        self.is_active = False
        self.input_timeout = 30.0  # seconds
        self.max_input_length = 8
        
        # Input handling
        self.input_timer = None
        self.on_pin_entered = None
        self.on_emergency_code = None
        self.on_admin_code = None
        self.on_voice_trigger = None
        self.on_timeout = None
        
        # Emergency and admin codes
        self.emergency_codes = ["*911*", "#999#"]
        self.admin_codes = ["*123*", "#456#"]
        self.voice_trigger_codes = ["*V*", "#V#"]
        
        # Input patterns
        self.special_patterns = {
            "**": "emergency_unlock",
            "##": "force_lock", 
            "*#": "admin_mode",
            "#*": "voice_mode",
            "00": "clear_input",
            "99": "system_status"
        }
        
        # Setup keypad callback
        self.keypad.set_key_callback(self._handle_key_press)
    
    async def start_input_session(self, mode: str = "normal", timeout: float = None):
        """
        Start a new input session
        
        Args:
            mode: Input mode (normal, emergency, admin, voice_trigger)
            timeout: Session timeout in seconds
        """
        if self.is_active:
            await self.end_input_session()
        
        self.input_mode = mode
        self.current_input = ""
        self.is_active = True
        
        if timeout:
            self.input_timeout = timeout
        
        # Visual feedback based on mode
        if mode == "normal":
            await self.led.set_status("ready")
        elif mode == "emergency":
            await self.led.set_status("emergency")
        elif mode == "admin":
            await self.led.set_status("admin")
        elif mode == "voice_trigger":
            await self.led.set_status("voice_active")
        
        # Audio feedback
        await self.buzzer.processing_sound()
        
        # Start timeout timer
        if self.input_timer:
            self.input_timer.cancel()
        
        self.input_timer = asyncio.create_task(self._input_timeout_handler())
        
        print(f"📱 Input session started - Mode: {mode}, Timeout: {self.input_timeout}s")
    
    async def end_input_session(self, reason: str = "completed"):
        """End current input session"""
        if not self.is_active:
            return
        
        self.is_active = False
        self.current_input = ""
        
        # Cancel timeout timer
        if self.input_timer:
            self.input_timer.cancel()
            self.input_timer = None
        
        # Reset visual state
        await self.led.set_status("idle")
        
        print(f"📱 Input session ended - Reason: {reason}")
    
    async def _handle_key_press(self, key: str):
        """Handle keypad key press"""
        if not self.is_active:
            return
        
        # Audio feedback for key press
        await self.buzzer.keypress_sound()
        
        # Visual feedback
        await self.led.pulse_color("blue", duration=0.1)
        
        print(f"🔑 Key pressed: {key}")
        
        # Handle special keys
        if key == "*":
            await self._handle_star_key()
        elif key == "#":
            await self._handle_hash_key()
        elif key == "A":
            await self._handle_admin_key()
        elif key == "B":
            await self._handle_back_key()
        elif key == "C":
            await self._handle_clear_key()
        elif key == "D":
            await self._handle_emergency_key()
        elif key.isdigit():
            await self._handle_digit_key(key)
        else:
            print(f"⚠️  Unknown key: {key}")
    
    async def _handle_digit_key(self, digit: str):
        """Handle numeric digit input"""
        if len(self.current_input) >= self.max_input_length:
            await self.buzzer.error_sound()
            await self.led.flash_color("red", count=2)
            return
        
        self.current_input += digit
        
        # Check for special patterns
        await self._check_special_patterns()
        
        # Visual feedback for input length
        if len(self.current_input) == 4:
            await self.led.pulse_color("yellow", duration=0.2)
        elif len(self.current_input) >= 6:
            await self.led.pulse_color("green", duration=0.2)
        
        print(f"📱 Current input: {'*' * len(self.current_input)}")
    
    async def _handle_star_key(self):
        """Handle star (*) key press"""
        self.current_input += "*"
        
        # Check for special patterns
        await self._check_special_patterns()
        
        # Check for emergency codes
        if self.current_input in self.emergency_codes:
            await self._handle_emergency_activation()
            return
        
        # Check for admin codes
        if self.current_input in self.admin_codes:
            await self._handle_admin_activation()
            return
        
        # Check for voice trigger codes
        if self.current_input in self.voice_trigger_codes:
            await self._handle_voice_trigger_activation()
            return
    
    async def _handle_hash_key(self):
        """Handle hash (#) key press - typically submit/enter"""
        if len(self.current_input) == 0:
            await self.buzzer.error_sound()
            return
        
        # If ending with #, treat as PIN submission
        if not self.current_input.endswith("#"):
            self.current_input += "#"
        
        # Check for special patterns first
        await self._check_special_patterns()
        
        # If it's a regular PIN (all digits + #)
        pin_content = self.current_input.rstrip("#")
        if pin_content.isdigit() and len(pin_content) >= 4:
            await self._submit_pin()
        else:
            await self.buzzer.error_sound()
            await self.led.flash_color("red", count=2)
    
    async def _handle_admin_key(self):
        """Handle A key - admin functions"""
        if self.input_mode != "admin":
            await self.start_input_session("admin")
        else:
            await self._show_system_status()
    
    async def _handle_back_key(self):
        """Handle B key - backspace/back"""
        if len(self.current_input) > 0:
            self.current_input = self.current_input[:-1]
            await self.buzzer.keypress_sound()
            await self.led.pulse_color("orange", duration=0.1)
            print(f"📱 Backspace - Current input: {'*' * len(self.current_input)}")
        else:
            await self.buzzer.error_sound()
    
    async def _handle_clear_key(self):
        """Handle C key - clear input"""
        self.current_input = ""
        await self.buzzer.processing_sound()
        await self.led.pulse_color("white", duration=0.2)
        print("📱 Input cleared")
    
    async def _handle_emergency_key(self):
        """Handle D key - emergency functions"""
        if self.input_mode != "emergency":
            await self.start_input_session("emergency")
        else:
            await self._emergency_unlock()
    
    async def _check_special_patterns(self):
        """Check for special input patterns"""
        for pattern, action in self.special_patterns.items():
            if self.current_input.endswith(pattern):
                await self._execute_special_action(action)
                return True
        return False
    
    async def _execute_special_action(self, action: str):
        """Execute special action based on pattern"""
        print(f"🔧 Executing special action: {action}")
        
        if action == "emergency_unlock":
            await self._emergency_unlock()
        elif action == "force_lock":
            await self._force_lock()
        elif action == "admin_mode":
            await self.start_input_session("admin")
        elif action == "voice_mode":
            await self.start_input_session("voice_trigger")
        elif action == "clear_input":
            await self._handle_clear_key()
        elif action == "system_status":
            await self._show_system_status()
    
    async def _submit_pin(self):
        """Submit PIN for verification"""
        pin = self.current_input.rstrip("#")
        
        print(f"📱 Submitting PIN: {'*' * len(pin)}")
        
        # Visual feedback for processing
        await self.led.set_status("processing")
        await self.buzzer.processing_sound()
        
        # Call PIN verification callback
        if self.on_pin_entered:
            try:
                result = await self.on_pin_entered(pin, self.input_mode)
                
                if result:
                    await self.led.set_status("success")
                    await self.buzzer.success_sound()
                    await self.end_input_session("pin_accepted")
                else:
                    await self.led.set_status("error")
                    await self.buzzer.error_sound()
                    await asyncio.sleep(2)
                    await self.start_input_session(self.input_mode)  # Restart session
            except Exception as e:
                print(f"❌ PIN verification error: {e}")
                await self.led.set_status("error")
                await self.buzzer.error_sound()
                await self.end_input_session("error")
        else:
            print("⚠️  No PIN verification handler set")
            await self.end_input_session("no_handler")
    
    async def _emergency_unlock(self):
        """Execute emergency unlock"""
        print("🚨 Emergency unlock activated!")
        
        await self.led.set_status("emergency")
        await self.buzzer.alarm_sound(2.0)
        
        # Execute emergency unlock
        await self.lock.emergency_unlock()
        
        # Call emergency callback
        if self.on_emergency_code:
            await self.on_emergency_code("emergency_unlock")
        
        await self.end_input_session("emergency_unlock")
    
    async def _force_lock(self):
        """Execute force lock"""
        print("🔒 Force lock activated!")
        
        await self.led.set_status("warning")
        await self.buzzer.warning_sound()
        
        # Execute force lock
        await self.lock.force_lock()
        
        await self.end_input_session("force_lock")
    
    async def _handle_emergency_activation(self):
        """Handle emergency code activation"""
        print("🚨 Emergency code detected!")
        
        await self.led.flash_color("red", count=5, interval=0.1)
        await self.buzzer.alarm_sound(1.0)
        
        if self.on_emergency_code:
            await self.on_emergency_code(self.current_input)
        
        await self.end_input_session("emergency_code")
    
    async def _handle_admin_activation(self):
        """Handle admin code activation"""
        print("🔧 Admin code detected!")
        
        await self.led.set_status("admin")
        await self.buzzer.notification_sound("high")
        
        if self.on_admin_code:
            await self.on_admin_code(self.current_input)
        
        await self.start_input_session("admin")
    
    async def _handle_voice_trigger_activation(self):
        """Handle voice trigger activation"""
        print("🎤 Voice trigger activated!")
        
        await self.led.set_status("voice_active")
        await self.buzzer.notification_sound("normal")
        
        if self.on_voice_trigger:
            await self.on_voice_trigger()
        
        await self.end_input_session("voice_trigger")
    
    async def _show_system_status(self):
        """Show system status via LED patterns"""
        print("📊 Showing system status...")
        
        # Get status from all components
        keypad_status = self.keypad.get_status()
        led_status = self.led.get_status()
        buzzer_status = self.buzzer.get_status()
        lock_status = self.lock.get_status()
        
        # Visual status indication
        if lock_status["is_locked"]:
            await self.led.pulse_color("red", duration=1.0)  # Locked
        else:
            await self.led.pulse_color("green", duration=1.0)  # Unlocked
        
        await asyncio.sleep(0.5)
        
        if lock_status["door_open"]:
            await self.led.pulse_color("yellow", duration=1.0)  # Door open
        else:
            await self.led.pulse_color("blue", duration=1.0)   # Door closed
        
        # Audio status
        await self.buzzer.notification_sound("normal")
        
        print(f"🔒 Lock: {'Locked' if lock_status['is_locked'] else 'Unlocked'}")
        print(f"🚪 Door: {'Open' if lock_status['door_open'] else 'Closed'}")
        print(f"💡 LED: {led_status['current_status']}")
        print(f"🔊 Buzzer: {'Available' if buzzer_status['available'] else 'Unavailable'}")
    
    async def _input_timeout_handler(self):
        """Handle input session timeout"""
        try:
            await asyncio.sleep(self.input_timeout)
            
            print("⏰ Input session timed out")
            
            await self.led.flash_color("orange", count=3)
            await self.buzzer.warning_sound()
            
            if self.on_timeout:
                await self.on_timeout()
            
            await self.end_input_session("timeout")
            
        except asyncio.CancelledError:
            pass  # Timer was cancelled
    
    def set_callbacks(self,
                     on_pin_entered: Optional[Callable] = None,
                     on_emergency_code: Optional[Callable] = None,
                     on_admin_code: Optional[Callable] = None,
                     on_voice_trigger: Optional[Callable] = None,
                     on_timeout: Optional[Callable] = None):
        """Set event callbacks"""
        self.on_pin_entered = on_pin_entered
        self.on_emergency_code = on_emergency_code
        self.on_admin_code = on_admin_code
        self.on_voice_trigger = on_voice_trigger
        self.on_timeout = on_timeout
    
    def set_emergency_codes(self, codes: List[str]):
        """Set emergency access codes"""
        self.emergency_codes = codes
    
    def set_admin_codes(self, codes: List[str]):
        """Set admin access codes"""
        self.admin_codes = codes
    
    def set_voice_trigger_codes(self, codes: List[str]):
        """Set voice trigger codes"""
        self.voice_trigger_codes = codes
    
    def get_status(self) -> dict:
        """Get input handler status"""
        return {
            "is_active": self.is_active,
            "input_mode": self.input_mode,
            "current_input_length": len(self.current_input),
            "input_timeout": self.input_timeout,
            "max_input_length": self.max_input_length,
            "emergency_codes": len(self.emergency_codes),
            "admin_codes": len(self.admin_codes),
            "voice_trigger_codes": len(self.voice_trigger_codes)
        }
    
    async def demo_sequence(self):
        """Demonstration sequence of input handler features"""
        print("🎭 Starting input handler demo...")
        
        # Demo normal PIN entry
        await self.start_input_session("normal")
        await asyncio.sleep(1)
        
        # Simulate PIN entry
        for digit in "1234":
            await self._handle_digit_key(digit)
            await asyncio.sleep(0.3)
        
        await self._handle_hash_key()  # Submit PIN
        await asyncio.sleep(2)
        
        # Demo emergency mode
        await self.start_input_session("emergency")
        await asyncio.sleep(1)
        await self.end_input_session("demo")
        
        # Demo admin mode
        await self.start_input_session("admin")
        await asyncio.sleep(1)
        await self._show_system_status()
        await self.end_input_session("demo")
        
        print("✅ Input handler demo completed")
    
    def cleanup(self):
        """Clean up resources"""
        if self.input_timer:
            self.input_timer.cancel()

# CLI testing interface
async def main():
    """CLI interface for input handler testing"""
    print("📱 Keypad Input Handler Test")
    print("=" * 35)
    
    # Initialize hardware controllers (simulation mode)
    keypad = KeypadController(simulation_mode=True)
    led = LEDController(simulation_mode=True)
    buzzer = BuzzerController(simulation_mode=True)
    lock = LockController(simulation_mode=True)
    
    # Initialize input handler
    input_handler = KeypadInputHandler(keypad, led, buzzer, lock)
    
    # Setup callbacks
    async def pin_entered(pin, mode):
        print(f"📱 PIN entered: {pin} (mode: {mode})")
        return pin == "1234"  # Accept only 1234 for demo
    
    async def emergency_code(code):
        print(f"🚨 Emergency code: {code}")
    
    async def admin_code(code):
        print(f"🔧 Admin code: {code}")
    
    async def voice_trigger():
        print(f"🎤 Voice trigger activated!")
    
    async def timeout():
        print(f"⏰ Input session timeout!")
    
    input_handler.set_callbacks(
        on_pin_entered=pin_entered,
        on_emergency_code=emergency_code,
        on_admin_code=admin_code,
        on_voice_trigger=voice_trigger,
        on_timeout=timeout
    )
    
    try:
        # Run demo sequence
        await input_handler.demo_sequence()
        
        # Show status
        status = input_handler.get_status()
        print(f"📊 Input Handler Status: {status}")
        
        print("✅ Input handler test completed")
        
    except KeyboardInterrupt:
        print("\n👋 Input handler test stopped")
    finally:
        input_handler.cleanup()
        keypad.cleanup()
        led.cleanup()
        buzzer.cleanup()
        lock.cleanup()

if __name__ == "__main__":
    asyncio.run(main())