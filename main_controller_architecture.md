# Main Controller Architecture - Smart Locker System

## 🎯 System Integration Overview

```
Smart Locker System Architecture:

┌─────────────────────────────────────────────────────────────┐
│                    MAIN CONTROLLER                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Voice AI Core  │  │  PIN Auth Core  │  │ Hardware I/O │ │
│  │                 │  │                 │  │              │ │
│  │ ▸ SpeakerRec    │  │ ▸ PINVerifier   │  │ ▸ Keypad     │ │
│  │ ▸ GMMScorer     │  │ ▸ AccessControl │  │ ▸ Lock       │ │
│  │ ▸ VoiceRec      │  │ ▸ UserMgmt      │  │ ▸ LEDs       │ │
│  └─────────────────┘  └─────────────────┘  │ ▸ Buzzer     │ │
│           │                      │         └──────────────┘ │
│           └──────────┬──────────────────────────────────────┘
│                      │
│  ┌─────────────────────────────────────────────────────────┐
│  │              AUTHENTICATION FLOW ENGINE                 │
│  │                                                         │
│  │  [A] Voice Recognition → PIN Entry → Access Grant       │
│  │  [B] Admin Mode → PIN Only → System Control            │
│  │  [C] Emergency → Master PIN → Override                 │
│  │  [D] Status Check → System Info → Display              │
│  └─────────────────────────────────────────────────────────┘
│
│  ┌─────────────────────────────────────────────────────────┐
│  │                WEB INTERFACE BRIDGE                     │
│  │                                                         │
│  │ ▸ Streamlit Admin Panel (Local Network)                │
│  │ ▸ Real-time Monitoring Dashboard                       │
│  │ ▸ User Management Interface                            │
│  │ ▸ Access Logs & Analytics                              │
│  └─────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Main Controller Implementation

### 1. main_controller.py

```python
import asyncio
import time
import logging
import json
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor

# Core AI and Authentication
from core.speaker_recognition import SpeakerRecognition
from core.gmm_speaker import GMMScorer
from core.voice_recorder import VoiceRecorder
from auth.pin_verification import PINVerification
from auth.access_control import AccessControl

# Hardware Controllers
from hardware.keypad_controller import KeypadController
from hardware.keypad_input import KeypadPINInput
from hardware.lock_controller import LockController
from hardware.led_controller import LEDController
from hardware.buzzer_controller import BuzzerController

# Configuration
from config.system_settings import SystemSettings
from config.security_config import SecurityConfig

class SmartLockerController:
    """
    Main orchestration controller for Smart Locker System
    Coordinates voice recognition, PIN authentication, and hardware control
    """
    
    def __init__(self, config_file: str = "config/system_config.json"):
        # Load configuration
        self.config = SystemSettings(config_file)
        self.security_config = SecurityConfig()
        
        # Initialize logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core AI Components
        self.voice_recorder = VoiceRecorder()
        self.speaker_recognition = SpeakerRecognition()
        self.gmm_scorer = GMMScorer()
        
        # Authentication System
        self.pin_verification = PINVerification()
        self.access_control = AccessControl()
        
        # Hardware Controllers
        self.keypad = KeypadController()
        self.keypad_input = KeypadPINInput(self.keypad)
        self.lock = LockController(status_callback=self.hardware_event_handler)
        self.leds = LEDController()
        self.buzzer = BuzzerController()
        
        # System State
        self.system_state = "initializing"
        self.current_session = None
        self.system_locked = False
        self.last_activity = time.time()
        
        # Event handlers
        self.event_handlers = {}
        self.setup_event_handlers()
        
        # Thread pool for blocking operations
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        self.logger.info("Smart Locker Controller initialized")
    
    def setup_logging(self):
        """Configure system logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/system.log'),
                logging.StreamHandler()
            ]
        )
    
    def setup_event_handlers(self):
        """Setup event handling callbacks"""
        self.event_handlers = {
            'keypad': self.handle_keypad_event,
            'voice': self.handle_voice_event,
            'hardware': self.hardware_event_handler,
            'security': self.handle_security_event,
            'system': self.handle_system_event
        }
    
    async def start_system(self):
        """Initialize and start the smart locker system"""
        try:
            self.logger.info("Starting Smart Locker System...")
            
            # Hardware initialization sequence
            await self.leds.startup_sequence()
            await self.buzzer.startup_sound()
            
            # System ready
            self.system_state = "ready"
            self.leds.set_status('ready')
            
            self.logger.info("✅ Smart Locker System ready")
            
            # Start main control loop
            await self.main_control_loop()
            
        except Exception as e:
            self.logger.error(f"System startup failed: {str(e)}")
            self.leds.set_status('error')
            await self.buzzer.error_sound()
            raise
    
    async def main_control_loop(self):
        """Main system control loop - handles keypad inputs and system events"""
        self.logger.info("Entering main control loop")
        
        while True:
            try:
                # Check for system lockdown
                if self.system_locked:
                    await self.handle_system_lockdown()
                    continue
                
                # Wait for keypad input with timeout
                key = await self.keypad.wait_for_key(timeout=1.0)
                
                if key:
                    await self.handle_keypad_input(key)
                    self.last_activity = time.time()
                else:
                    # Check for idle timeout
                    await self.check_idle_timeout()
                
                # Background tasks
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in main control loop: {str(e)}")
                await asyncio.sleep(1.0)
    
    async def handle_keypad_input(self, key: str):
        """Handle keypad key press events"""
        await self.buzzer.keypress_sound()
        
        # Function keys
        if key == 'A':
            await self.start_voice_recognition_flow()
        elif key == 'B':
            await self.start_admin_mode()
        elif key == 'C':
            await self.show_system_status()
        elif key == 'D':
            await self.start_emergency_mode()
        else:
            # Regular numeric/symbol keys handled by specific flows
            pass
    
    async def start_voice_recognition_flow(self):
        """Start voice recognition + PIN authentication flow"""
        self.logger.info("Starting voice recognition flow")
        self.current_session = {
            "id": f"session_{int(time.time())}",
            "start_time": time.time(),
            "method": "voice_pin",
            "stage": "voice_recognition"
        }
        
        try:
            # Step 1: Voice Recognition
            self.leds.set_status('processing')
            await self.buzzer.processing_sound()
            
            # Record voice sample
            audio_data = await self.record_voice_sample()
            if not audio_data:
                await self.authentication_failed("voice_recording_failed")
                return
            
            # Identify user
            user_id, voice_confidence = await self.identify_user(audio_data)
            if not user_id:
                await self.authentication_failed("voice_not_recognized")
                return
            
            # Get GMM score
            gmm_score = await self.get_gmm_score(user_id, audio_data)
            
            self.logger.info(f"Voice recognized: {user_id} (confidence: {voice_confidence:.3f})")
            
            # Step 2: PIN Authentication
            self.current_session.update({
                "user_id": user_id,
                "voice_confidence": voice_confidence,
                "gmm_score": gmm_score,
                "stage": "pin_entry"
            })
            
            await self.request_pin_input(user_id)
            
        except Exception as e:
            self.logger.error(f"Voice recognition flow failed: {str(e)}")
            await self.authentication_failed("system_error")
    
    async def record_voice_sample(self) -> Optional[bytes]:
        """Record voice sample for recognition"""
        try:
            # Visual/audio feedback
            await self.leds.pulse_status('processing', duration=1.0)
            
            # Record audio in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                self.executor, 
                self.voice_recorder.record_audio,
                5.0  # 5 second recording
            )
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Voice recording failed: {str(e)}")
            return None
    
    async def identify_user(self, audio_data: bytes) -> tuple[Optional[str], float]:
        """Identify user from voice sample"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self.speaker_recognition.identify_speaker,
                audio_data
            )
            
            if result:
                return result['user_id'], result['confidence']
            return None, 0.0
            
        except Exception as e:
            self.logger.error(f"User identification failed: {str(e)}")
            return None, 0.0
    
    async def get_gmm_score(self, user_id: str, audio_data: bytes) -> float:
        """Get GMM confidence score"""
        try:
            loop = asyncio.get_event_loop()
            score = await loop.run_in_executor(
                self.executor,
                self.gmm_scorer.score_user,
                user_id, audio_data
            )
            return score
        except Exception as e:
            self.logger.error(f"GMM scoring failed: {str(e)}")
            return 0.0
    
    async def request_pin_input(self, user_id: str):
        """Request PIN input from user"""
        self.logger.info(f"Requesting PIN for user: {user_id}")
        
        # Visual feedback
        self.leds.set_status('warning')  # Orange for PIN entry
        
        # Get PIN input with visual feedback
        pin = await self.keypad_input.get_pin_input(
            prompt_callback=self.pin_input_callback
        )
        
        if pin:
            await self.verify_pin_and_grant_access(user_id, pin)
        else:
            await self.authentication_failed("pin_timeout")
    
    async def pin_input_callback(self, event: str, data: dict):
        """Handle PIN input visual feedback"""
        if event == "pin_input":
            # Blink blue LED for each digit
            await self.leds.blink_status('processing', duration=0.1)
        elif event == "pin_confirmed":
            await self.buzzer.processing_sound()
        elif event == "pin_cancelled":
            self.leds.set_status('error')
            await self.buzzer.error_sound()
    
    async def verify_pin_and_grant_access(self, user_id: str, pin: str):
        """Verify PIN and grant access if successful"""
        # Complete authentication
        auth_result = self.access_control.authenticate_user(
            user_id=user_id,
            voice_confidence=self.current_session['voice_confidence'],
            gmm_score=self.current_session['gmm_score'],
            pin=pin
        )
        
        if auth_result['success']:
            await self.grant_access(user_id, auth_result)
        else:
            await self.authentication_failed(auth_result['reason'])
    
    async def grant_access(self, user_id: str, auth_result: dict):
        """Grant access and unlock door"""
        self.logger.info(f"✅ Access granted to user: {user_id}")
        
        # Success feedback
        self.leds.set_status('success')
        await self.buzzer.success_sound()
        
        # Unlock door
        unlock_duration = self.config.get('door_unlock_duration', 5.0)
        await self.lock.unlock_door(duration=unlock_duration)
        
        # Update session
        self.current_session.update({
            "status": "success",
            "end_time": time.time(),
            "auth_result": auth_result
        })
        
        # Log access
        self.log_access_event(self.current_session)
        
        # Reset for next user
        await asyncio.sleep(2.0)
        self.reset_session()
    
    async def authentication_failed(self, reason: str):
        """Handle authentication failure"""
        self.logger.warning(f"❌ Authentication failed: {reason}")
        
        # Error feedback
        self.leds.set_status('error')
        await self.buzzer.error_sound()
        
        # Update session
        if self.current_session:
            self.current_session.update({
                "status": "failed",
                "reason": reason,
                "end_time": time.time()
            })
            self.log_access_event(self.current_session)
        
        # Reset after delay
        await asyncio.sleep(3.0)
        self.reset_session()
    
    async def start_admin_mode(self):
        """Start administrator mode"""
        self.logger.info("Entering admin mode")
        
        self.leds.set_status('admin')
        
        # Get admin PIN
        admin_pin = await self.keypad_input.get_admin_pin(
            prompt_callback=self.admin_pin_callback
        )
        
        if admin_pin:
            # Verify admin PIN
            if self.verify_admin_pin(admin_pin):
                await self.enter_admin_interface()
            else:
                await self.authentication_failed("invalid_admin_pin")
        else:
            self.reset_session()
    
    async def admin_pin_callback(self, event: str, data: dict):
        """Handle admin PIN input feedback"""
        if event == "admin_pin_input":
            await self.leds.blink_status('admin', duration=0.1)
    
    def verify_admin_pin(self, pin: str) -> bool:
        """Verify admin PIN"""
        return pin == self.security_config.get_admin_pin()
    
    async def enter_admin_interface(self):
        """Enter admin interface mode"""
        self.logger.info("✅ Admin access granted")
        
        # Success feedback
        await self.buzzer.success_sound()
        self.leds.set_status('success')
        
        # Show admin menu (simplified for keypad)
        await self.show_admin_menu()
    
    async def show_admin_menu(self):
        """Show admin menu options"""
        # Admin menu via LEDs and buzzer patterns
        # 1 = Add user, 2 = Remove user, 3 = System info, etc.
        pass
    
    async def start_emergency_mode(self):
        """Start emergency unlock mode"""
        self.logger.warning("🚨 Emergency mode activated")
        
        # Emergency feedback
        self.leds.set_status('error')
        await self.buzzer.warning_sound()
        
        # Get emergency PIN
        emergency_pin = await self.keypad_input.get_admin_pin()
        
        if emergency_pin:
            # Emergency unlock
            result = self.access_control.emergency_unlock(emergency_pin)
            
            if result['success']:
                await self.lock.emergency_unlock()
                self.logger.info("🚨 Emergency unlock successful")
            else:
                await self.authentication_failed("invalid_emergency_pin")
        else:
            self.reset_session()
    
    async def show_system_status(self):
        """Show system status via LED patterns"""
        status = self.get_system_status()
        
        # Show status via LED blink patterns
        if status['door_open']:
            await self.leds.blink_status('warning', duration=2.0)
        elif status['lock_engaged']:
            await self.leds.blink_status('ready', duration=2.0)
        else:
            await self.leds.blink_status('error', duration=2.0)
    
    def get_system_status(self) -> dict:
        """Get comprehensive system status"""
        return {
            "timestamp": time.time(),
            "system_state": self.system_state,
            "door_open": self.lock.is_door_open(),
            "lock_engaged": self.lock.is_door_locked(),
            "last_activity": self.last_activity,
            "current_session": bool(self.current_session),
            "system_locked": self.system_locked
        }
    
    async def hardware_event_handler(self, event: str, data: dict):
        """Handle hardware events from controllers"""
        self.logger.info(f"Hardware event: {event}")
        
        if event == "door_opened":
            await self.buzzer.processing_sound()
        elif event == "door_closed":
            self.leds.set_status('ready')
        elif event == "door_timeout":
            await self.buzzer.alarm_sound(2.0)
            self.leds.set_status('error')
    
    async def check_idle_timeout(self):
        """Check for system idle timeout"""
        idle_time = time.time() - self.last_activity
        max_idle = self.config.get('max_idle_time', 300)  # 5 minutes
        
        if idle_time > max_idle:
            await self.enter_low_power_mode()
    
    async def enter_low_power_mode(self):
        """Enter low power mode to save energy"""
        self.logger.info("Entering low power mode")
        self.leds.set_status('off')
        # Reduce scan frequency, etc.
    
    async def handle_system_lockdown(self):
        """Handle system lockdown state"""
        # Flash error pattern
        await self.leds.blink_status('error', duration=1.0)
        await asyncio.sleep(5.0)  # Lockdown period
    
    def reset_session(self):
        """Reset current session"""
        self.current_session = None
        self.leds.set_status('ready')
        self.logger.debug("Session reset")
    
    def log_access_event(self, session: dict):
        """Log access event to file"""
        try:
            with open('logs/access_events.log', 'a') as f:
                f.write(f"{json.dumps(session)}\n")
        except Exception as e:
            self.logger.error(f"Failed to log access event: {str(e)}")
    
    async def shutdown_system(self):
        """Gracefully shutdown the system"""
        self.logger.info("Shutting down Smart Locker System")
        
        # Cleanup hardware
        self.keypad.cleanup()
        self.lock.cleanup()
        self.leds.cleanup()
        self.buzzer.cleanup()
        
        # Close executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("System shutdown complete")

# Main entry point
async def main():
    """Main entry point for Smart Locker System"""
    controller = SmartLockerController()
    
    try:
        await controller.start_system()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"System error: {str(e)}")
    finally:
        await controller.shutdown_system()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    import signal
    
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main controller
    asyncio.run(main())
```

### 2. config/system_settings.py

```python
import json
from typing import Dict, Any

class SystemSettings:
    """System configuration management"""
    
    def __init__(self, config_file: str = "config/system_config.json"):
        self.config_file = config_file
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_settings()
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default system settings"""
        return {
            "voice_recognition": {
                "confidence_threshold": 0.7,
                "recording_duration": 5.0,
                "max_attempts": 3
            },
            "pin_authentication": {
                "max_attempts": 3,
                "lockout_duration": 300,
                "pin_timeout": 30
            },
            "hardware": {
                "door_unlock_duration": 5.0,
                "led_brightness": 0.5,
                "buzzer_volume": 0.7
            },
            "security": {
                "max_idle_time": 300,
                "emergency_unlock_duration": 60,
                "system_lockdown_failures": 10
            },
            "logging": {
                "log_level": "INFO",
                "max_log_size": "10MB",
                "backup_count": 5
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value by key"""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def save_settings(self):
        """Save current settings to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
```

### 3. config/security_config.py

```python
import os
import hashlib
from typing import Optional

class SecurityConfig:
    """Security configuration and secrets management"""
    
    def __init__(self):
        self.admin_pin_hash = self._get_admin_pin_hash()
    
    def _get_admin_pin_hash(self) -> str:
        """Get admin PIN hash from environment or default"""
        # Try to get from environment variable
        admin_pin = os.getenv('LOCKER_ADMIN_PIN', '0000')
        return hashlib.sha256(admin_pin.encode()).hexdigest()
    
    def get_admin_pin(self) -> str:
        """Get admin PIN (fallback method)"""
        return os.getenv('LOCKER_ADMIN_PIN', '0000')
    
    def verify_admin_pin(self, pin: str) -> bool:
        """Verify admin PIN"""
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        return pin_hash == self.admin_pin_hash
```

## 🚀 System Startup Script

### start_locker.py

```python
#!/usr/bin/env python3
"""
Smart Locker System Startup Script
Handles system initialization, dependency checks, and service startup
"""

import sys
import os
import time
import asyncio
import logging
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        'RPi.GPIO', 'speechbrain', 'torch', 'torchaudio',
        'librosa', 'sklearn', 'streamlit', 'bcrypt'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module.replace('.', '_') if '.' in module else module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Run: pip install -r requirements_rpi.txt")
        return False
    
    return True

def check_hardware():
    """Check if running on Raspberry Pi with GPIO access"""
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
        return True
    except Exception as e:
        print(f"❌ Hardware check failed: {str(e)}")
        print("Make sure you're running on Raspberry Pi with GPIO access")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = [
        'logs', 'data', 'data/gmm_models', 'config'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def setup_permissions():
    """Set up file permissions"""
    # Ensure audio device access
    os.system("sudo usermod -a -G audio pi")
    os.system("sudo usermod -a -G gpio pi")

async def start_locker_system():
    """Start the main locker system"""
    from main_controller import SmartLockerController
    
    controller = SmartLockerController()
    await controller.start_system()

def main():
    """Main startup function"""
    print("🔐 Smart Locker System - Starting...")
    
    # Pre-flight checks
    if not check_dependencies():
        sys.exit(1)
    
    if not check_hardware():
        print("⚠️  Hardware check failed - running in simulation mode")
    
    # Setup
    setup_directories()
    
    # Start system
    try:
        asyncio.run(start_locker_system())
    except KeyboardInterrupt:
        print("\n👋 Smart Locker System stopped by user")
    except Exception as e:
        print(f"💥 System error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📋 Implementation Summary

### Completed Architecture Components:

1. **✅ PIN Verification System** - Complete authentication core
2. **✅ Hardware Controllers** - GPIO control for all peripherals  
3. **✅ Main Controller** - System orchestration and flow control
4. **✅ Configuration Management** - Settings and security configs
5. **✅ Startup Scripts** - System initialization and checks

### Integration Flow:

```
[Keypad Press] → [Main Controller] → [Voice AI / PIN Auth] → [Hardware Response]
      ↓                ↓                      ↓                      ↓
   Key 'A'        Voice Flow           ECAPA + GMM + PIN        LED + Buzzer + Lock
   Key 'B'        Admin Mode           Admin PIN Only           Status Indicators  
   Key 'C'        Status Check         System Info              LED Patterns
   Key 'D'        Emergency            Emergency PIN            Emergency Unlock
```

### Ready for Implementation:

Semua dokumentasi dan arsitektur telah siap. Langkah selanjutnya adalah beralih ke mode **Code** untuk implementasi aktual semua modul yang telah dirancang.
