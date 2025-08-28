#!/usr/bin/env python3
"""
Test script to verify import fixes for Smart Locker System
"""

def test_imports():
    """Test all critical imports"""
    print("🧪 Testing Smart Locker System imports...")
    
    # Test hardware imports
    try:
        from hardware.keypad_controller import KeypadController
        from hardware.led_controller import LEDController
        from hardware.buzzer_controller import BuzzerController
        from hardware.lock_controller import LockController, LockManager
        from hardware.keypad_input import KeypadInputHandler
        print("✅ Hardware imports successful")
    except Exception as e:
        print(f"❌ Hardware import error: {e}")
        return False
    
    # Test auth imports
    try:
        from auth.pin_verification import PINVerification
        from auth.access_control import AccessControl
        print("✅ Auth imports successful")
    except Exception as e:
        print(f"❌ Auth import error: {e}")
        return False
    
    # Test main controller import
    try:
        from main_controller import SmartLockerController
        print("✅ Main controller import successful")
    except Exception as e:
        print(f"❌ Main controller import error: {e}")
        return False
    
    # Test instantiation
    try:
        controller = SmartLockerController(simulation_mode=True)
        print("✅ Controller instantiation successful")
    except Exception as e:
        print(f"❌ Controller instantiation error: {e}")
        return False
    
    print("🎉 All imports and instantiation tests passed!")
    return True

if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)