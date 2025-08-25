import asyncio
import pytest

# Import system components
from main_controller import SmartLockerController, SystemState, AuthenticationResult
from auth.pin_verification import PINVerifier
from auth.access_control import AccessController
from hardware.keypad_controller import KeypadController
from hardware.led_controller import LEDController
from hardware.buzzer_controller import BuzzerController
from hardware.lock_controller import LockController, LockManager
from hardware.keypad_input import KeypadInputHandler

class TestSmartLockerIntegration:
    """Comprehensive integration tests for Smart Locker System"""
    
    @pytest.fixture
    async def smart_locker(self):
        """Create Smart Locker instance for testing"""
        controller = SmartLockerController(simulation_mode=True)
        await controller.initialize()
        yield controller
        await controller.shutdown()
    
    @pytest.fixture
    def mock_audio_data(self):
        """Mock audio data for testing"""
        return b"mock_audio_data_for_testing" * 100
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, smart_locker):
        """Test system initialization"""
        assert smart_locker.current_state == SystemState.IDLE
        assert smart_locker.simulation_mode is True
        assert smart_locker.keypad is not None
        assert smart_locker.led is not None
        assert smart_locker.buzzer is not None
        assert smart_locker.lock is not None
        assert smart_locker.input_handler is not None
        assert smart_locker.pin_verifier is not None
        assert smart_locker.access_controller is not None
    
    @pytest.mark.asyncio
    async def test_pin_only_authentication_success(self, smart_locker):
        """Test successful PIN-only authentication"""
        # Setup test user with PIN
        pin_verifier = smart_locker.pin_verifier
        await pin_verifier.set_user_pin("test_user", "1234")
        
        # Simulate PIN entry
        result = await smart_locker._handle_pin_entered("1234", "normal")
        
        assert result is True
        assert smart_locker.current_state == SystemState.ACCESS_GRANTED
        assert smart_locker.lock.get_lock_state() is False  # Should be unlocked
    
    @pytest.mark.asyncio
    async def test_pin_authentication_failure(self, smart_locker):
        """Test failed PIN authentication"""
        # Setup test user with PIN
        pin_verifier = smart_locker.pin_verifier
        await pin_verifier.set_user_pin("test_user", "1234")
        
        # Simulate wrong PIN entry
        result = await smart_locker._handle_pin_entered("9999", "normal")
        
        assert result is False
        assert smart_locker.auth_attempts > 0
        assert smart_locker.lock.get_lock_state() is True  # Should remain locked
    
    @pytest.mark.asyncio
    async def test_emergency_unlock(self, smart_locker):
        """Test emergency unlock functionality"""
        # Ensure lock is initially locked
        await smart_locker.lock.lock()
        assert smart_locker.lock.get_lock_state() is True
        
        # Trigger emergency unlock
        await smart_locker._handle_emergency_code("*911*")
        
        assert smart_locker.current_state == SystemState.EMERGENCY
        assert smart_locker.lock.get_lock_state() is False  # Should be unlocked
    
    @pytest.mark.asyncio
    async def test_admin_mode_activation(self, smart_locker):
        """Test admin mode activation"""
        # Setup admin PIN
        access_controller = smart_locker.access_controller
        await access_controller.pin_verifier.set_admin_pin("admin123")
        
        # Activate admin mode
        await smart_locker._handle_admin_code("*123*")
        assert smart_locker.current_state == SystemState.ADMIN_MODE
        
        # Verify admin PIN
        result = await smart_locker._handle_pin_entered("admin123", "admin")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_voice_trigger_activation(self, smart_locker):
        """Test voice trigger activation"""
        # Trigger voice authentication mode
        await smart_locker._handle_voice_trigger()
        
        assert smart_locker.current_state == SystemState.VOICE_AUTHENTICATION
    
    @pytest.mark.asyncio
    async def test_door_sensor_events(self, smart_locker):
        """Test door sensor event handling"""
        lock_controller = smart_locker.lock
        
        # Test door opened event
        lock_controller._handle_door_opened()
        assert lock_controller.door_open is True
        
        # Test door closed event  
        lock_controller._handle_door_closed()
        assert lock_controller.door_open is False
    
    @pytest.mark.asyncio
    async def test_auto_lock_functionality(self, smart_locker):
        """Test automatic lock after timeout"""
        lock_controller = smart_locker.lock
        
        # Unlock with auto-lock delay
        await lock_controller.unlock(auto_lock_delay=1.0)
        assert lock_controller.get_lock_state() is False
        
        # Wait for auto-lock
        await asyncio.sleep(1.5)
        assert lock_controller.get_lock_state() is True
    
    @pytest.mark.asyncio
    async def test_input_timeout_handling(self, smart_locker):
        """Test input session timeout"""
        input_handler = smart_locker.input_handler
        
        # Start input session with short timeout
        await input_handler.start_input_session("normal", timeout=0.5)
        assert input_handler.is_active is True
        
        # Wait for timeout
        await asyncio.sleep(1.0)
        assert input_handler.is_active is False
    
    @pytest.mark.asyncio
    async def test_max_auth_attempts_lockout(self, smart_locker):
        """Test system lockout after max failed attempts"""
        initial_attempts = smart_locker.auth_attempts
        max_attempts = smart_locker.max_auth_attempts
        
        # Simulate failed attempts
        for i in range(max_attempts):
            await smart_locker._authentication_failed(f"Test failure {i+1}")
        
        # Should trigger lockout
        assert smart_locker.auth_attempts == 0  # Reset after lockout
    
    @pytest.mark.asyncio
    async def test_hardware_controllers_integration(self, smart_locker):
        """Test hardware controllers integration"""
        # Test LED controller
        await smart_locker.led.set_status("ready")
        status = smart_locker.led.get_status()
        assert status["simulation_mode"] is True
        
        # Test buzzer controller
        await smart_locker.buzzer.processing_sound()
        buzzer_status = smart_locker.buzzer.get_status()
        assert "simulation_mode" in buzzer_status
        
        # Test keypad controller
        keypad_status = smart_locker.keypad.get_status()
        assert "simulation_mode" in keypad_status
        
        # Test lock controller
        lock_status = smart_locker.lock.get_status()
        assert "simulation_mode" in lock_status
    
    @pytest.mark.asyncio
    async def test_access_logging(self, smart_locker):
        """Test access attempt logging"""
        lock_manager = smart_locker.lock_manager
        
        # Grant access
        await lock_manager.grant_access("test_user", "test_method", 30.0)
        
        # Check access log
        access_log = lock_manager.get_access_log(limit=1)
        assert len(access_log) > 0
        assert access_log[-1]["user_id"] == "test_user"
        assert access_log[-1]["method"] == "test_method"
        assert access_log[-1]["granted"] is True
    
    @pytest.mark.asyncio
    async def test_system_status_reporting(self, smart_locker):
        """Test system status reporting"""
        status = smart_locker.get_system_status()
        
        assert "current_state" in status
        assert "simulation_mode" in status
        assert "hardware_status" in status
        assert "auth_attempts" in status
        assert "last_activity" in status
        
        # Check hardware status
        hw_status = status["hardware_status"]
        assert "keypad" in hw_status
        assert "led" in hw_status
        assert "buzzer" in hw_status
        assert "lock" in hw_status
    
    @pytest.mark.asyncio
    async def test_state_transitions(self, smart_locker):
        """Test system state transitions"""
        # Test state transition from IDLE to VOICE_AUTHENTICATION
        initial_state = smart_locker.current_state
        await smart_locker._set_state(SystemState.VOICE_AUTHENTICATION)
        
        assert smart_locker.previous_state == initial_state
        assert smart_locker.current_state == SystemState.VOICE_AUTHENTICATION
        
        # Test transition to PIN_AUTHENTICATION
        await smart_locker._set_state(SystemState.PIN_AUTHENTICATION)
        assert smart_locker.current_state == SystemState.PIN_AUTHENTICATION
        
        # Test transition to ACCESS_GRANTED
        await smart_locker._set_state(SystemState.ACCESS_GRANTED)
        assert smart_locker.current_state == SystemState.ACCESS_GRANTED
    
    @pytest.mark.asyncio
    async def test_configuration_loading(self, smart_locker):
        """Test configuration loading and validation"""
        config = smart_locker.config
        
        # Check essential configuration values
        assert "voice_timeout" in config
        assert "pin_timeout" in config
        assert "access_duration" in config
        assert "max_auth_attempts" in config
        assert "emergency_codes" in config
        assert "admin_codes" in config
        
        # Check default values
        assert config["voice_timeout"] > 0
        assert config["pin_timeout"] > 0
        assert config["access_duration"] > 0
        assert config["max_auth_attempts"] > 0

class TestKeypadInputIntegration:
    """Test keypad input handler integration"""
    
    @pytest.fixture
    async def input_system(self):
        """Create input system for testing"""
        keypad = KeypadController(simulation_mode=True)
        led = LEDController(simulation_mode=True)
        buzzer = BuzzerController(simulation_mode=True)
        lock = LockController(simulation_mode=True)
        
        input_handler = KeypadInputHandler(keypad, led, buzzer, lock)
        
        yield input_handler, keypad, led, buzzer, lock
        
        # Cleanup
        input_handler.cleanup()
        keypad.cleanup()
        led.cleanup()
        buzzer.cleanup()
        lock.cleanup()
    
    @pytest.mark.asyncio
    async def test_keypad_input_flow(self, input_system):
        """Test complete keypad input flow"""
        input_handler, keypad, led, buzzer, lock = input_system
        
        # Start input session
        await input_handler.start_input_session("normal", 10.0)
        assert input_handler.is_active is True
        
        # Simulate digit entry
        await input_handler._handle_digit_key("1")
        await input_handler._handle_digit_key("2")
        await input_handler._handle_digit_key("3")
        await input_handler._handle_digit_key("4")
        
        assert len(input_handler.current_input) == 4
        
        # End session
        await input_handler.end_input_session("test_complete")
        assert input_handler.is_active is False
    
    @pytest.mark.asyncio
    async def test_special_key_handling(self, input_system):
        """Test special key handling"""
        input_handler, keypad, led, buzzer, lock = input_system
        
        await input_handler.start_input_session("normal", 10.0)
        
        # Test clear key
        await input_handler._handle_digit_key("1")
        await input_handler._handle_clear_key()
        assert len(input_handler.current_input) == 0
        
        # Test backspace key
        await input_handler._handle_digit_key("1")
        await input_handler._handle_digit_key("2")
        await input_handler._handle_back_key()
        assert len(input_handler.current_input) == 1
        assert input_handler.current_input == "1"
    
    @pytest.mark.asyncio
    async def test_emergency_pattern_detection(self, input_system):
        """Test emergency pattern detection"""
        input_handler, keypad, led, buzzer, lock = input_system
        
        # Setup emergency callback
        emergency_triggered = False
        
        async def emergency_callback(code):
            nonlocal emergency_triggered
            emergency_triggered = True
        
        input_handler.on_emergency_code = emergency_callback
        
        # Start session and enter emergency pattern
        await input_handler.start_input_session("normal", 10.0)
        
        # Simulate emergency code entry
        for char in "*911*":
            if char == "*":
                await input_handler._handle_star_key()
            else:
                await input_handler._handle_digit_key(char)
        
        assert emergency_triggered is True

class TestHardwareControllersIntegration:
    """Test hardware controllers integration"""
    
    @pytest.mark.asyncio
    async def test_led_buzzer_coordination(self):
        """Test LED and buzzer coordination"""
        led = LEDController(simulation_mode=True)
        buzzer = BuzzerController(simulation_mode=True)
        
        try:
            # Test success pattern
            await led.set_status("success")
            await buzzer.success_sound()
            
            # Test error pattern
            await led.set_status("error")
            await buzzer.error_sound()
            
            # Test warning pattern
            await led.set_status("warning")
            await buzzer.warning_sound()
            
            # Verify states
            led_status = led.get_status()
            buzzer_status = buzzer.get_status()
            
            assert led_status["simulation_mode"] is True
            assert buzzer_status["simulation_mode"] is True
            
        finally:
            led.cleanup()
            buzzer.cleanup()
    
    @pytest.mark.asyncio
    async def test_lock_led_integration(self):
        """Test lock and LED status integration"""
        lock = LockController(simulation_mode=True)
        led = LEDController(simulation_mode=True)
        
        try:
            # Setup lock state change callback
            async def lock_state_changed(locked):
                if locked:
                    await led.set_status("locked")
                else:
                    await led.set_status("unlocked")
            
            lock.on_lock_changed = lock_state_changed
            
            # Test unlock
            await lock.unlock()
            assert lock.get_lock_state() is False
            
            # Test lock
            await lock.lock()
            assert lock.get_lock_state() is True
            
        finally:
            lock.cleanup()
            led.cleanup()

# Utility functions for testing
async def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Smart Locker Integration Tests")
    print("=" * 50)
    
    # Run pytest programmatically
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            __file__, 
            "-v", 
            "--asyncio-mode=auto"
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

async def manual_integration_test():
    """Manual integration test for demonstration"""
    print("🔧 Manual Integration Test")
    print("=" * 30)
    
    # Initialize system
    controller = SmartLockerController(simulation_mode=True)
    
    try:
        # Initialize system
        print("📱 Initializing system...")
        await controller.initialize()
        
        # Test PIN authentication
        print("🔑 Testing PIN authentication...")
        await controller.pin_verifier.set_user_pin("demo_user", "1234")
        
        # Simulate PIN entry
        result = await controller._handle_pin_entered("1234", "normal")
        print(f"PIN Auth Result: {result}")
        
        # Test emergency unlock
        print("🚨 Testing emergency unlock...")
        await controller._handle_emergency_code("*911*")
        
        # Test system status
        print("📊 System Status:")
        status = controller.get_system_status()
        for key, value in status.items():
            if key != "hardware_status":
                print(f"  {key}: {value}")
        
        # Test hardware integration
        print("🔧 Testing hardware integration...")
        await controller.led.flash_color("green", count=3)
        await controller.buzzer.success_sound()
        
        print("✅ Manual integration test completed successfully")
        
    except Exception as e:
        print(f"❌ Manual integration test failed: {e}")
        
    finally:
        await controller.shutdown()

# CLI interface
async def main():
    """Main CLI interface for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Locker Integration Tests")
    parser.add_argument("--manual", action="store_true", help="Run manual integration test")
    parser.add_argument("--auto", action="store_true", help="Run automated pytest tests")
    
    args = parser.parse_args()
    
    if args.manual:
        await manual_integration_test()
    elif args.auto:
        success = await run_integration_tests()
        exit(0 if success else 1)
    else:
        print("Smart Locker Integration Test Suite")
        print("Options:")
        print("  --manual  Run manual integration test")
        print("  --auto    Run automated pytest tests")

if __name__ == "__main__":
    asyncio.run(main())