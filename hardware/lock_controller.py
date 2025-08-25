import asyncio
import time
from typing import Optional, Callable
from datetime import datetime, timedelta
from .hardware_config import (
    SOLENOID_LOCK_PIN, 
    DOOR_SENSOR_PIN, 
    DOOR_OPEN_TIMEOUT,
    SOLENOID_ACTIVE_LOW
)

# Try to import RPi.GPIO, fallback to simulation mode if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - Lock controller running in simulation mode")

class LockController:
    """
    Solenoid Lock Controller for Smart Locker
    Controls electronic lock with door sensor monitoring
    Supports simulation mode when RPi.GPIO is not available
    """
    
    def __init__(self, simulation_mode=None):
        self.solenoid_pin = SOLENOID_LOCK_PIN
        self.door_sensor_pin = DOOR_SENSOR_PIN
        self.door_timeout = DOOR_OPEN_TIMEOUT
        self.active_low = SOLENOID_ACTIVE_LOW
        
        # Lock state
        self.is_locked = True
        self.door_open = False
        self.auto_lock_timer = None
        self.door_open_timer = None
        
        # Callbacks
        self.on_door_opened = None
        self.on_door_closed = None
        self.on_door_timeout = None
        self.on_lock_changed = None
        
        # Determine if we should use simulation mode
        if simulation_mode is None:
            self.simulation_mode = not GPIO_AVAILABLE
        else:
            self.simulation_mode = simulation_mode
        
        if not self.simulation_mode:
            self.setup_gpio()
        else:
            print("🔧 Lock controller running in simulation mode")
    
    def setup_gpio(self):
        """Initialize GPIO pins for lock and door sensor"""
        if self.simulation_mode:
            return
        
        GPIO.setmode(GPIO.BCM)
        
        # Setup solenoid lock pin
        GPIO.setup(self.solenoid_pin, GPIO.OUT)
        self._set_lock_state(True)  # Start locked
        
        # Setup door sensor pin with pull-up resistor
        GPIO.setup(self.door_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup door sensor interrupt
        GPIO.add_event_detect(
            self.door_sensor_pin, 
            GPIO.BOTH, 
            callback=self._door_sensor_callback,
            bouncetime=200
        )
        
        # Read initial door state
        self.door_open = not GPIO.input(self.door_sensor_pin)  # Assuming sensor is LOW when door is open
    
    def _set_lock_state(self, locked: bool):
        """Set physical lock state"""
        if self.simulation_mode:
            self.is_locked = locked
            print(f"🔒 Lock {'LOCKED' if locked else 'UNLOCKED'}")
            return
        
        # Set solenoid state (considering active low configuration)
        if self.active_low:
            GPIO.output(self.solenoid_pin, not locked)
        else:
            GPIO.output(self.solenoid_pin, locked)
        
        self.is_locked = locked
    
    def _door_sensor_callback(self, channel):
        """GPIO interrupt callback for door sensor changes"""
        if self.simulation_mode:
            return
        
        # Read door state (assuming LOW = open, HIGH = closed)
        door_state = not GPIO.input(self.door_sensor_pin)
        
        if door_state != self.door_open:
            self.door_open = door_state
            
            if self.door_open:
                self._handle_door_opened()
            else:
                self._handle_door_closed()
    
    def _handle_door_opened(self):
        """Handle door opened event"""
        print("🚪 Door opened")
        
        # Cancel any existing door timer
        if self.door_open_timer:
            self.door_open_timer.cancel()
        
        # Start door timeout timer
        self.door_open_timer = asyncio.create_task(self._door_timeout_handler())
        
        # Call callback if set
        if self.on_door_opened:
            asyncio.create_task(self.on_door_opened())
    
    def _handle_door_closed(self):
        """Handle door closed event"""
        print("🚪 Door closed")
        
        # Cancel door timeout timer
        if self.door_open_timer:
            self.door_open_timer.cancel()
            self.door_open_timer = None
        
        # Call callback if set
        if self.on_door_closed:
            asyncio.create_task(self.on_door_closed())
    
    async def _door_timeout_handler(self):
        """Handle door open timeout"""
        try:
            await asyncio.sleep(self.door_timeout)
            
            if self.door_open:  # Door is still open after timeout
                print("⚠️  Door open timeout!")
                
                # Auto-lock if unlocked
                if not self.is_locked:
                    await self.lock()
                    print("🔒 Auto-locked due to door timeout")
                
                # Call timeout callback if set
                if self.on_door_timeout:
                    await self.on_door_timeout()
        
        except asyncio.CancelledError:
            pass  # Timer was cancelled (door closed)
    
    async def unlock(self, auto_lock_delay: Optional[float] = None):
        """
        Unlock the door
        
        Args:
            auto_lock_delay: Seconds to wait before auto-locking (None = no auto-lock)
        """
        if not self.is_locked:
            print("🔓 Already unlocked")
            return True
        
        print("🔓 Unlocking door...")
        self._set_lock_state(False)
        
        # Simulate door sensor change in simulation mode
        if self.simulation_mode:
            # Simulate brief delay then door opening
            await asyncio.sleep(0.5)
            old_state = self.door_open
            self.door_open = True
            if not old_state:
                self._handle_door_opened()
        
        # Setup auto-lock timer if specified
        if auto_lock_delay:
            if self.auto_lock_timer:
                self.auto_lock_timer.cancel()
            
            self.auto_lock_timer = asyncio.create_task(
                self._auto_lock_handler(auto_lock_delay)
            )
        
        # Call lock state change callback
        if self.on_lock_changed:
            await self.on_lock_changed(False)
        
        return True
    
    async def lock(self):
        """Lock the door"""
        if self.is_locked:
            print("🔒 Already locked")
            return True
        
        print("🔒 Locking door...")
        self._set_lock_state(True)
        
        # Cancel auto-lock timer if running
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
        
        # Simulate door sensor change in simulation mode
        if self.simulation_mode:
            await asyncio.sleep(0.2)
            old_state = self.door_open
            self.door_open = False
            if old_state:
                self._handle_door_closed()
        
        # Call lock state change callback
        if self.on_lock_changed:
            await self.on_lock_changed(True)
        
        return True
    
    async def _auto_lock_handler(self, delay: float):
        """Handle auto-lock after delay"""
        try:
            await asyncio.sleep(delay)
            
            # Auto-lock only if door is closed
            if not self.door_open:
                await self.lock()
                print(f"🔒 Auto-locked after {delay} seconds")
            else:
                print("⚠️  Auto-lock delayed - door is open")
                # Retry auto-lock when door closes
                self.auto_lock_timer = asyncio.create_task(
                    self._auto_lock_handler(5.0)  # Retry in 5 seconds
                )
        
        except asyncio.CancelledError:
            pass  # Timer was cancelled
    
    async def emergency_unlock(self):
        """Emergency unlock (bypasses normal checks)"""
        print("🚨 Emergency unlock activated!")
        self._set_lock_state(False)
        
        # Cancel all timers
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
        
        if self.door_open_timer:
            self.door_open_timer.cancel()
            self.door_open_timer = None
        
        # Call lock state change callback
        if self.on_lock_changed:
            await self.on_lock_changed(False)
        
        return True
    
    async def force_lock(self):
        """Force lock (even if door is open)"""
        print("🔒 Force lock activated!")
        self._set_lock_state(True)
        
        # Cancel timers
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
        
        # Call lock state change callback
        if self.on_lock_changed:
            await self.on_lock_changed(True)
        
        return True
    
    def is_door_open(self) -> bool:
        """Check if door is currently open"""
        if self.simulation_mode:
            return self.door_open
        
        return not GPIO.input(self.door_sensor_pin)
    
    def get_lock_state(self) -> bool:
        """Get current lock state"""
        return self.is_locked
    
    def get_status(self) -> dict:
        """Get comprehensive lock system status"""
        return {
            "simulation_mode": self.simulation_mode,
            "lock_pin": self.solenoid_pin,
            "door_sensor_pin": self.door_sensor_pin,
            "is_locked": self.is_locked,
            "door_open": self.door_open,
            "door_timeout": self.door_timeout,
            "active_low": self.active_low,
            "auto_lock_active": self.auto_lock_timer is not None,
            "door_timeout_active": self.door_open_timer is not None,
            "gpio_available": GPIO_AVAILABLE
        }
    
    def set_callbacks(self, 
                     on_door_opened: Optional[Callable] = None,
                     on_door_closed: Optional[Callable] = None,
                     on_door_timeout: Optional[Callable] = None,
                     on_lock_changed: Optional[Callable] = None):
        """Set event callbacks"""
        self.on_door_opened = on_door_opened
        self.on_door_closed = on_door_closed
        self.on_door_timeout = on_door_timeout
        self.on_lock_changed = on_lock_changed
    
    async def test_sequence(self):
        """Test lock/unlock sequence"""
        print("🔧 Testing lock sequence...")
        
        # Test unlock
        await self.unlock()
        await asyncio.sleep(2)
        
        # Test lock
        await self.lock()
        await asyncio.sleep(1)
        
        # Test unlock with auto-lock
        await self.unlock(auto_lock_delay=3.0)
        await asyncio.sleep(5)  # Wait for auto-lock
        
        print("✅ Lock test sequence completed")
    
    async def simulate_door_activity(self):
        """Simulate door opening/closing for testing"""
        if not self.simulation_mode:
            print("⚠️  Door simulation only available in simulation mode")
            return
        
        print("🚪 Simulating door activity...")
        
        # Simulate door opening
        old_state = self.door_open
        self.door_open = True
        if not old_state:
            self._handle_door_opened()
        
        await asyncio.sleep(2)
        
        # Simulate door closing
        old_state = self.door_open
        self.door_open = False
        if old_state:
            self._handle_door_closed()
        
        print("✅ Door simulation completed")
    
    def cleanup(self):
        """Clean up GPIO resources and timers"""
        # Cancel timers
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
        
        if self.door_open_timer:
            self.door_open_timer.cancel()
        
        # Clean up GPIO
        if not self.simulation_mode and GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(self.door_sensor_pin)
                GPIO.setup(self.solenoid_pin, GPIO.IN)
                GPIO.setup(self.door_sensor_pin, GPIO.IN)
                GPIO.cleanup()
            except Exception as e:
                print(f"⚠️  Lock GPIO cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass

# Lock management utilities
class LockManager:
    """High-level lock management with access control"""
    
    def __init__(self, lock_controller: LockController):
        self.lock = lock_controller
        self.access_log = []
        self.failed_attempts = 0
        self.last_unlock_time = None
        self.lockout_until = None
    
    async def grant_access(self, user_id: str, access_method: str, duration: float = 30.0):
        """
        Grant access to a user
        
        Args:
            user_id: User identifier
            access_method: How access was granted (voice, pin, keycard, etc.)
            duration: How long to keep unlocked (seconds)
        """
        if self.lockout_until and datetime.now() < self.lockout_until:
            remaining = (self.lockout_until - datetime.now()).total_seconds()
            print(f"🚫 System locked out for {remaining:.0f} more seconds")
            return False
        
        # Log access attempt
        self.access_log.append({
            "timestamp": datetime.now(),
            "user_id": user_id,
            "method": access_method,
            "granted": True
        })
        
        # Reset failed attempts on successful access
        self.failed_attempts = 0
        self.last_unlock_time = datetime.now()
        
        # Unlock with auto-lock
        await self.lock.unlock(auto_lock_delay=duration)
        
        print(f"✅ Access granted to {user_id} via {access_method} for {duration}s")
        return True
    
    async def deny_access(self, user_id: str, reason: str):
        """
        Deny access to a user
        
        Args:
            user_id: User identifier  
            reason: Reason for denial
        """
        # Log failed attempt
        self.access_log.append({
            "timestamp": datetime.now(),
            "user_id": user_id,
            "method": "unknown",
            "granted": False,
            "reason": reason
        })
        
        self.failed_attempts += 1
        
        # Implement lockout after too many failed attempts
        if self.failed_attempts >= 5:
            self.lockout_until = datetime.now() + timedelta(minutes=10)
            print(f"🚫 System locked out for 10 minutes due to {self.failed_attempts} failed attempts")
        
        print(f"❌ Access denied for {user_id}: {reason}")
        return False
    
    def get_access_log(self, limit: int = 50) -> list:
        """Get recent access log entries"""
        return self.access_log[-limit:]
    
    def get_stats(self) -> dict:
        """Get access statistics"""
        total_attempts = len(self.access_log)
        successful = sum(1 for entry in self.access_log if entry["granted"])
        
        return {
            "total_attempts": total_attempts,
            "successful_access": successful,
            "failed_attempts": total_attempts - successful,
            "current_failed_streak": self.failed_attempts,
            "last_unlock": self.last_unlock_time,
            "lockout_until": self.lockout_until,
            "is_locked_out": self.lockout_until and datetime.now() < self.lockout_until
        }

# CLI testing interface
async def main():
    """CLI interface for lock testing"""
    print("🔒 Lock Controller Test")
    print("=" * 30)
    
    # Test basic lock controller
    lock = LockController()
    
    # Setup callbacks
    async def door_opened():
        print("📢 Callback: Door opened!")
    
    async def door_closed():
        print("📢 Callback: Door closed!")
    
    async def door_timeout():
        print("📢 Callback: Door timeout!")
    
    async def lock_changed(locked):
        state = "locked" if locked else "unlocked"
        print(f"📢 Callback: Lock state changed to {state}")
    
    lock.set_callbacks(
        on_door_opened=door_opened,
        on_door_closed=door_closed,
        on_door_timeout=door_timeout,
        on_lock_changed=lock_changed
    )
    
    try:
        # Test basic operations
        print("Testing basic lock operations...")
        await lock.test_sequence()
        await asyncio.sleep(1)
        
        # Test door simulation
        if lock.simulation_mode:
            await lock.simulate_door_activity()
            await asyncio.sleep(1)
        
        # Test lock manager
        print("Testing lock manager...")
        manager = LockManager(lock)
        
        await manager.grant_access("user123", "voice", 10.0)
        await asyncio.sleep(2)
        
        await manager.deny_access("unknown", "invalid PIN")
        await asyncio.sleep(1)
        
        # Show stats
        stats = manager.get_stats()
        print(f"📊 Access Stats: {stats}")
        
        # Show status
        status = lock.get_status()
        print(f"🔍 Lock Status: {status}")
        
        print("✅ Lock test completed")
        
    except KeyboardInterrupt:
        print("\n👋 Lock test stopped")
    finally:
        lock.cleanup()

if __name__ == "__main__":
    asyncio.run(main())