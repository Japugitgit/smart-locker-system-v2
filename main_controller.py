import asyncio
import logging
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Import hardware controllers
from hardware.keypad_controller import KeypadController
from hardware.led_controller import LEDController
from hardware.buzzer_controller import BuzzerController
from hardware.lock_controller import LockController, LockManager
from hardware.keypad_input import KeypadInputHandler

# Import authentication modules
from auth.pin_verification import PINVerifier
from auth.access_control import AccessController

# Import voice recognition modules
from speaker_recognition import SpeakerRecognition
from voice_recorder import VoiceRecorder
from gmm_speaker import GMMScorer

class SystemState(Enum):
    """System operation states"""
    STARTUP = "startup"
    IDLE = "idle"
    VOICE_AUTHENTICATION = "voice_auth"
    PIN_AUTHENTICATION = "pin_auth"
    ACCESS_GRANTED = "access_granted"
    EMERGENCY = "emergency"
    ADMIN_MODE = "admin"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    SHUTDOWN = "shutdown"

@dataclass
class AuthenticationResult:
    """Authentication result data structure"""
    success: bool
    user_id: Optional[str] = None
    method: str = "unknown"
    confidence: float = 0.0
    gmm_score: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None

class SmartLockerController:
    """
    Main Smart Locker System Controller
    Orchestrates voice recognition, PIN verification, and hardware control
    Manages system states and authentication flows
    """
    
    def __init__(self, simulation_mode: bool = None):
        # System configuration
        self.simulation_mode = simulation_mode
        self.current_state = SystemState.STARTUP
        self.previous_state = None
        
        # Configuration
        self.config = self._load_config()
        self.voice_timeout = self.config.get("voice_timeout", 10.0)
        self.pin_timeout = self.config.get("pin_timeout", 30.0)
        self.access_duration = self.config.get("access_duration", 30.0)
        self.max_auth_attempts = self.config.get("max_auth_attempts", 3)
        
        # Authentication state
        self.auth_attempts = 0
        self.current_user = None
        self.last_activity = datetime.now()
        self.session_active = False
        
        # Hardware controllers
        self.keypad = None
        self.led = None
        self.buzzer = None
        self.lock = None
        self.lock_manager = None
        self.input_handler = None
        
        # Authentication modules
        self.pin_verifier = None
        self.access_controller = None
        self.speaker_recognition = None
        self.voice_recorder = None
        self.gmm_scorer = None
        
        # System tasks
        self.main_task = None
        self.watchdog_task = None
        self.cleanup_task = None
        
        # Event handlers
        self.event_handlers = {}
        
        # Logging
        self._setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load system configuration"""
        config_path = "config/smart_locker_config.json"
        default_config = {
            "voice_timeout": 10.0,
            "pin_timeout": 30.0,
            "access_duration": 30.0,
            "max_auth_attempts": 3,
            "voice_threshold": 0.75,
            "gmm_enabled": True,
            "auto_lock_delay": 10.0,
            "emergency_codes": ["*911*", "#999#"],
            "admin_codes": ["*123*", "#456#"],
            "voice_trigger_codes": ["*V*", "#V#"],
            "hardware_simulation": None,
            "debug_mode": False
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    return {**default_config, **config}
            else:
                # Create default config file
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            logging.getLogger("SmartLocker").warning(f"Failed to load config: {e}, using defaults")
            return default_config
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if not self.config.get("debug_mode") else logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{log_dir}/smart_locker.log"),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("SmartLocker")
    
    async def initialize(self):
        """Initialize all system components"""
        self.logger.info("🚀 Initializing Smart Locker System...")
        
        try:
            # Determine simulation mode
            if self.simulation_mode is None:
                self.simulation_mode = self.config.get("hardware_simulation", None)
            
            # Initialize hardware controllers
            await self._initialize_hardware()
            
            # Initialize authentication modules
            await self._initialize_authentication()
            
            # Setup event handlers
            self._setup_event_handlers()
            
            # Start system tasks
            await self._start_system_tasks()
            
            # Set initial state
            await self._set_state(SystemState.IDLE)
            
            self.logger.info("✅ Smart Locker System initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ System initialization failed: {e}")
            await self._set_state(SystemState.ERROR)
            raise
    
    async def _initialize_hardware(self):
        """Initialize hardware controllers"""
        self.logger.info("🔧 Initializing hardware controllers...")
        
        # Initialize controllers
        self.keypad = KeypadController(simulation_mode=self.simulation_mode)
        self.led = LEDController(simulation_mode=self.simulation_mode)
        self.buzzer = BuzzerController(simulation_mode=self.simulation_mode)
        self.lock = LockController(simulation_mode=self.simulation_mode)
        
        # Initialize lock manager
        self.lock_manager = LockManager(self.lock)
        
        # Initialize input handler
        self.input_handler = KeypadInputHandler(
            self.keypad, self.led, self.buzzer, self.lock
        )
        
        # Configure input handler
        self.input_handler.set_emergency_codes(self.config["emergency_codes"])
        self.input_handler.set_admin_codes(self.config["admin_codes"])
        self.input_handler.set_voice_trigger_codes(self.config["voice_trigger_codes"])
        
        self.logger.info("✅ Hardware controllers initialized")
    
    async def _initialize_authentication(self):
        """Initialize authentication modules"""
        self.logger.info("🔐 Initializing authentication modules...")
        
        # Initialize PIN verifier
        self.pin_verifier = PINVerifier()
        
        # Initialize access controller
        self.access_controller = AccessController(self.pin_verifier)
        
        # Initialize voice recognition
        self.speaker_recognition = SpeakerRecognition()
        self.voice_recorder = VoiceRecorder()
        
        # Initialize GMM scorer if enabled
        if self.config.get("gmm_enabled", True):
            self.gmm_scorer = GMMScorer()
        
        self.logger.info("✅ Authentication modules initialized")
    
    def _setup_event_handlers(self):
        """Setup event handlers for input and hardware events"""
        # Input handler callbacks
        self.input_handler.set_callbacks(
            on_pin_entered=self._handle_pin_entered,
            on_emergency_code=self._handle_emergency_code,
            on_admin_code=self._handle_admin_code,
            on_voice_trigger=self._handle_voice_trigger,
            on_timeout=self._handle_input_timeout
        )
        
        # Lock callbacks
        self.lock.set_callbacks(
            on_door_opened=self._handle_door_opened,
            on_door_closed=self._handle_door_closed,
            on_door_timeout=self._handle_door_timeout,
            on_lock_changed=self._handle_lock_changed
        )
    
    async def _start_system_tasks(self):
        """Start background system tasks"""
        # Main system loop
        self.main_task = asyncio.create_task(self._main_loop())
        
        # System watchdog
        self.watchdog_task = asyncio.create_task(self._watchdog_loop())
        
        # Cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _main_loop(self):
        """Main system event loop"""
        self.logger.info("🔄 Starting main system loop...")
        
        try:
            while True:
                # Update activity timestamp
                self.last_activity = datetime.now()
                
                # State-specific logic
                if self.current_state == SystemState.IDLE:
                    await self._handle_idle_state()
                elif self.current_state == SystemState.VOICE_AUTHENTICATION:
                    await self._handle_voice_auth_state()
                elif self.current_state == SystemState.PIN_AUTHENTICATION:
                    await self._handle_pin_auth_state()
                elif self.current_state == SystemState.ACCESS_GRANTED:
                    await self._handle_access_granted_state()
                elif self.current_state == SystemState.EMERGENCY:
                    await self._handle_emergency_state()
                elif self.current_state == SystemState.ADMIN_MODE:
                    await self._handle_admin_state()
                elif self.current_state == SystemState.ERROR:
                    await self._handle_error_state()
                
                # Sleep briefly to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            self.logger.info("Main loop cancelled")
        except Exception as e:
            self.logger.error(f"Main loop error: {e}")
            await self._set_state(SystemState.ERROR)
    
    async def _handle_idle_state(self):
        """Handle idle state - waiting for user interaction"""
        if not self.input_handler.is_active:
            await self.input_handler.start_input_session("normal", self.pin_timeout)
        
        # Show idle status
        await self.led.set_status("ready")
    
    async def _handle_voice_auth_state(self):
        """Handle voice authentication state"""
        self.logger.info("🎤 Starting voice authentication...")
        
        try:
            # Set visual feedback
            await self.led.set_status("voice_active")
            await self.buzzer.notification_sound("normal")
            
            # Record voice sample
            self.logger.info("📱 Recording voice sample...")
            audio_data = await self._record_voice_sample()
            
            if audio_data is None:
                await self._authentication_failed("Voice recording failed")
                return
            
            # Perform voice recognition
            auth_result = await self._perform_voice_authentication(audio_data)
            
            if auth_result.success:
                # Voice authentication successful, proceed to PIN
                self.current_user = auth_result.user_id
                await self._set_state(SystemState.PIN_AUTHENTICATION)
                await self.led.set_status("voice_success")
                await self.buzzer.success_sound()
                
                self.logger.info(f"✅ Voice authentication successful for user: {auth_result.user_id}")
            else:
                await self._authentication_failed(auth_result.error_message or "Voice authentication failed")
        
        except Exception as e:
            self.logger.error(f"Voice authentication error: {e}")
            await self._authentication_failed(f"Voice authentication error: {e}")
    
    async def _handle_pin_auth_state(self):
        """Handle PIN authentication state"""
        if not self.input_handler.is_active:
            await self.input_handler.start_input_session("normal", self.pin_timeout)
            await self.led.set_status("pin_required")
            await self.buzzer.notification_sound("normal")
    
    async def _handle_access_granted_state(self):
        """Handle access granted state"""
        # This state is managed by the lock controller's auto-lock timer
        pass
    
    async def _handle_emergency_state(self):
        """Handle emergency state"""
        await self.led.set_status("emergency")
        # Emergency state handling is done in emergency callbacks
        await asyncio.sleep(1)
        await self._set_state(SystemState.IDLE)
    
    async def _handle_admin_state(self):
        """Handle admin mode state"""
        if not self.input_handler.is_active:
            await self.input_handler.start_input_session("admin", self.pin_timeout)
            await self.led.set_status("admin")
    
    async def _handle_error_state(self):
        """Handle error state"""
        await self.led.set_status("error")
        await asyncio.sleep(5)  # Stay in error state for 5 seconds
        await self._set_state(SystemState.IDLE)
    
    async def _record_voice_sample(self) -> Optional[bytes]:
        """Record voice sample for authentication"""
        try:
            # Start recording
            await self.voice_recorder.start_recording()
            
            # Record for specified duration
            await asyncio.sleep(self.voice_timeout)
            
            # Stop recording and get audio data
            audio_data = await self.voice_recorder.stop_recording()
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Voice recording error: {e}")
            return None
    
    async def _perform_voice_authentication(self, audio_data: bytes) -> AuthenticationResult:
        """Perform voice authentication"""
        try:
            # Get voice recognition result
            result = await self.speaker_recognition.identify_speaker(audio_data)
            
            if not result or not result.get("recognized"):
                return AuthenticationResult(
                    success=False,
                    error_message="Voice not recognized"
                )
            
            user_id = result.get("user_id")
            confidence = result.get("confidence", 0.0)
            
            # Check confidence threshold
            if confidence < self.config.get("voice_threshold", 0.75):
                return AuthenticationResult(
                    success=False,
                    user_id=user_id,
                    confidence=confidence,
                    error_message=f"Voice confidence too low: {confidence:.2f}"
                )
            
            # Get GMM score if available
            gmm_score = None
            if self.gmm_scorer:
                try:
                    gmm_score = await self.gmm_scorer.score_audio(user_id, audio_data)
                except Exception as e:
                    self.logger.warning(f"GMM scoring failed: {e}")
            
            return AuthenticationResult(
                success=True,
                user_id=user_id,
                method="voice",
                confidence=confidence,
                gmm_score=gmm_score,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Voice authentication error: {e}")
            return AuthenticationResult(
                success=False,
                error_message=f"Authentication error: {e}"
            )
    
    async def _handle_pin_entered(self, pin: str, mode: str) -> bool:
        """Handle PIN entry from keypad"""
        try:
            self.logger.info(f"🔑 PIN entered in {mode} mode")
            
            if mode == "admin":
                # Admin PIN verification
                result = await self.access_controller.verify_admin_pin(pin)
                if result.success:
                    await self._admin_access_granted()
                    return True
                else:
                    await self._authentication_failed("Invalid admin PIN")
                    return False
            
            elif self.current_user:
                # Regular user PIN verification after voice auth
                result = await self.access_controller.authenticate_user(
                    user_id=self.current_user,
                    pin=pin,
                    method="voice+pin"
                )
                
                if result.success:
                    await self._access_granted(self.current_user, "voice+pin")
                    return True
                else:
                    await self._authentication_failed("Invalid PIN")
                    return False
            
            else:
                # PIN-only authentication
                result = await self.access_controller.authenticate_pin_only(pin)
                
                if result.success:
                    await self._access_granted(result.user_id, "pin")
                    return True
                else:
                    await self._authentication_failed("Invalid PIN")
                    return False
                    
        except Exception as e:
            self.logger.error(f"PIN verification error: {e}")
            await self._authentication_failed(f"PIN verification error: {e}")
            return False
    
    async def _handle_emergency_code(self, code: str):
        """Handle emergency code activation"""
        self.logger.warning(f"🚨 Emergency code activated: {code}")
        
        await self._set_state(SystemState.EMERGENCY)
        await self.lock.emergency_unlock()
        
        # Log emergency access
        await self.access_controller.log_access_attempt(
            user_id="EMERGENCY",
            method="emergency_code",
            success=True,
            details={"code": code}
        )
    
    async def _handle_admin_code(self, code: str):
        """Handle admin code activation"""
        self.logger.info(f"🔧 Admin code activated: {code}")
        await self._set_state(SystemState.ADMIN_MODE)
    
    async def _handle_voice_trigger(self):
        """Handle voice trigger activation"""
        self.logger.info("🎤 Voice trigger activated")
        await self._set_state(SystemState.VOICE_AUTHENTICATION)
    
    async def _handle_input_timeout(self):
        """Handle input timeout"""
        self.logger.info("⏰ Input timeout")
        await self._set_state(SystemState.IDLE)
        self.auth_attempts += 1
        
        if self.auth_attempts >= self.max_auth_attempts:
            await self._lockout_activated()
    
    async def _handle_door_opened(self):
        """Handle door opened event"""
        self.logger.info("🚪 Door opened")
        await self.buzzer.door_sound("open")
    
    async def _handle_door_closed(self):
        """Handle door closed event"""
        self.logger.info("🚪 Door closed")
        await self.buzzer.door_sound("close")
    
    async def _handle_door_timeout(self):
        """Handle door open timeout"""
        self.logger.warning("⚠️ Door open timeout")
        await self.buzzer.door_sound("timeout")
        await self.led.flash_color("orange", count=5)
    
    async def _handle_lock_changed(self, locked: bool):
        """Handle lock state change"""
        state = "locked" if locked else "unlocked"
        self.logger.info(f"🔒 Lock state changed: {state}")
        await self.buzzer.door_sound("lock" if locked else "unlock")
    
    async def _access_granted(self, user_id: str, method: str):
        """Handle successful access"""
        self.logger.info(f"✅ Access granted to {user_id} via {method}")
        
        # Grant access via lock manager
        await self.lock_manager.grant_access(user_id, method, self.access_duration)
        
        # Set state and feedback
        await self._set_state(SystemState.ACCESS_GRANTED)
        await self.led.set_status("success")
        await self.buzzer.authentication_sound("granted")
        
        # Reset authentication state
        self.auth_attempts = 0
        self.current_user = None
        
        # Auto return to idle after access duration
        asyncio.create_task(self._auto_return_to_idle())
    
    async def _admin_access_granted(self):
        """Handle admin access granted"""
        self.logger.info("🔧 Admin access granted")
        
        await self.led.set_status("admin")
        await self.buzzer.authentication_sound("granted")
        
        # Keep in admin mode
        await self._set_state(SystemState.ADMIN_MODE)
    
    async def _authentication_failed(self, reason: str):
        """Handle authentication failure"""
        self.logger.warning(f"❌ Authentication failed: {reason}")
        
        self.auth_attempts += 1
        self.current_user = None
        
        await self.led.set_status("error")
        await self.buzzer.authentication_sound("denied")
        
        if self.auth_attempts >= self.max_auth_attempts:
            await self._lockout_activated()
        else:
            await asyncio.sleep(2)
            await self._set_state(SystemState.IDLE)
    
    async def _lockout_activated(self):
        """Handle system lockout"""
        self.logger.warning(f"🚫 System lockout after {self.auth_attempts} failed attempts")
        
        await self.led.flash_color("red", count=10, interval=0.2)
        await self.buzzer.alarm_sound(5.0)
        
        # Reset attempts after lockout
        self.auth_attempts = 0
        
        # Return to idle after lockout period
        await asyncio.sleep(10)
        await self._set_state(SystemState.IDLE)
    
    async def _auto_return_to_idle(self):
        """Auto return to idle state after access duration"""
        await asyncio.sleep(self.access_duration + 5)  # Extra 5 seconds buffer
        
        if self.current_state == SystemState.ACCESS_GRANTED:
            await self._set_state(SystemState.IDLE)
    
    async def _set_state(self, new_state: SystemState):
        """Set system state with logging"""
        if self.current_state != new_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.logger.info(f"🔄 State changed: {self.previous_state.value} → {new_state.value}")
            
            # End current input session when changing states
            if self.input_handler and self.input_handler.is_active:
                await self.input_handler.end_input_session("state_change")
    
    async def _watchdog_loop(self):
        """System watchdog to monitor health"""
        self.logger.info("🐕 Starting system watchdog...")
        
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                
                # Check system health
                await self._check_system_health()
                
        except asyncio.CancelledError:
            self.logger.info("Watchdog cancelled")
        except Exception as e:
            self.logger.error(f"Watchdog error: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup tasks"""
        self.logger.info("🧹 Starting cleanup loop...")
        
        try:
            while True:
                await asyncio.sleep(3600)  # Run every hour
                
                # Cleanup old logs, temporary files, etc.
                await self._perform_cleanup()
                
        except asyncio.CancelledError:
            self.logger.info("Cleanup loop cancelled")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    async def _check_system_health(self):
        """Check system component health"""
        try:
            # Check hardware status
            keypad_status = self.keypad.get_status()
            led_status = self.led.get_status()
            buzzer_status = self.buzzer.get_status()
            lock_status = self.lock.get_status()
            
            # Log health status
            self.logger.debug(f"System health - Keypad: OK, LED: {led_status['current_status']}, "
                             f"Buzzer: {'OK' if buzzer_status['available'] else 'FAIL'}, "
                             f"Lock: {'Locked' if lock_status['is_locked'] else 'Unlocked'}")
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            await self._set_state(SystemState.ERROR)
    
    async def _perform_cleanup(self):
        """Perform periodic cleanup tasks"""
        try:
            # Cleanup access logs (keep last 1000 entries)
            access_log = self.lock_manager.get_access_log()
            if len(access_log) > 1000:
                self.lock_manager.access_log = access_log[-1000:]
            
            self.logger.debug("Periodic cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "simulation_mode": self.simulation_mode,
            "auth_attempts": self.auth_attempts,
            "current_user": self.current_user,
            "session_active": self.session_active,
            "last_activity": self.last_activity.isoformat(),
            "hardware_status": {
                "keypad": self.keypad.get_status() if self.keypad else None,
                "led": self.led.get_status() if self.led else None,
                "buzzer": self.buzzer.get_status() if self.buzzer else None,
                "lock": self.lock.get_status() if self.lock else None
            },
            "input_handler_status": self.input_handler.get_status() if self.input_handler else None,
            "access_stats": self.lock_manager.get_stats() if self.lock_manager else None
        }
    
    async def shutdown(self):
        """Gracefully shutdown the system"""
        self.logger.info("🛑 Shutting down Smart Locker System...")
        
        await self._set_state(SystemState.SHUTDOWN)
        
        # Cancel background tasks
        if self.main_task:
            self.main_task.cancel()
        if self.watchdog_task:
            self.watchdog_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            self.main_task, self.watchdog_task, self.cleanup_task,
            return_exceptions=True
        )
        
        # Cleanup hardware
        if self.input_handler:
            self.input_handler.cleanup()
        if self.keypad:
            self.keypad.cleanup()
        if self.led:
            self.led.cleanup()
        if self.buzzer:
            self.buzzer.cleanup()
        if self.lock:
            self.lock.cleanup()
        
        self.logger.info("✅ System shutdown completed")

# CLI interface for testing
async def main():
    """CLI interface for Smart Locker testing"""
    print("🏠 Smart Locker System")
    print("=" * 30)
    
    # Initialize system
    controller = SmartLockerController(simulation_mode=True)
    
    try:
        # Initialize and start system
        await controller.initialize()
        
        # System startup sound
        await controller.buzzer.startup_sound()
        
        print("✅ Smart Locker System running")
        print("Press Ctrl+C to shutdown")
        
        # Run system
        while True:
            await asyncio.sleep(1)
            
            # Print status every 30 seconds
            if int(datetime.now().timestamp()) % 30 == 0:
                status = controller.get_system_status()
                print(f"📊 Status: {status['current_state']} | "
                      f"Attempts: {status['auth_attempts']} | "
                      f"User: {status.get('current_user', 'None')}")
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        await controller.shutdown()

if __name__ == "__main__":
    asyncio.run(main())