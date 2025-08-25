import asyncio
import time
from typing import Optional
from .hardware_config import BUZZER_PIN, BUZZER_VOLUME

# Try to import RPi.GPIO, fallback to simulation mode if not available
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - Buzzer controller running in simulation mode")

class BuzzerController:
    """
    Audio Buzzer Controller for Smart Locker
    Provides audio feedback for system events
    Supports simulation mode when RPi.GPIO is not available
    """
    
    def __init__(self, simulation_mode=None):
        self.buzzer_pin = BUZZER_PIN
        self.volume = BUZZER_VOLUME
        self.pwm = None
        
        # Determine if we should use simulation mode
        if simulation_mode is None:
            self.simulation_mode = not GPIO_AVAILABLE
        else:
            self.simulation_mode = simulation_mode
        
        if not self.simulation_mode:
            self.setup_gpio()
        else:
            print("🔧 Buzzer controller running in simulation mode")
    
    def setup_gpio(self):
        """Initialize GPIO pin for buzzer control"""
        if self.simulation_mode:
            return
        
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
        
        if self.simulation_mode:
            print(f"🔊 BEEP: {frequency}Hz for {duration:.2f}s at {volume:.1%} volume")
            return
        
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
        
        if self.simulation_mode:
            print(f"🔊 ASYNC BEEP: {frequency}Hz for {duration:.2f}s at {volume:.1%}")
            await asyncio.sleep(duration)
            return
        
        self.pwm.ChangeFrequency(frequency)
        duty_cycle = volume * 50
        self.pwm.ChangeDutyCycle(duty_cycle)
        
        await asyncio.sleep(duration)
        self.pwm.ChangeDutyCycle(0)
    
    async def success_sound(self):
        """Success sound pattern - ascending tones"""
        if self.simulation_mode:
            print("🎵 SUCCESS SOUND: Ascending tones")
            await asyncio.sleep(0.6)
            return
        
        frequencies = [800, 1000, 1200]
        for freq in frequencies:
            await self.async_beep(freq, 0.15)
            await asyncio.sleep(0.05)
    
    async def error_sound(self):
        """Error sound pattern - descending tones"""
        if self.simulation_mode:
            print("🎵 ERROR SOUND: Descending tones")
            await asyncio.sleep(0.9)
            return
        
        frequencies = [1200, 1000, 800]
        for freq in frequencies:
            await self.async_beep(freq, 0.2)
            await asyncio.sleep(0.1)
    
    async def warning_sound(self):
        """Warning sound pattern - alternating tones"""
        if self.simulation_mode:
            print("🎵 WARNING SOUND: Alternating tones")
            await asyncio.sleep(1.8)
            return
        
        for _ in range(3):
            await self.async_beep(800, 0.1)
            await asyncio.sleep(0.1)
            await self.async_beep(1200, 0.1)
            await asyncio.sleep(0.1)
    
    async def processing_sound(self):
        """Processing sound - single short beep"""
        if self.simulation_mode:
            print("🎵 PROCESSING SOUND")
            await asyncio.sleep(0.05)
            return
        
        await self.async_beep(1000, 0.05)
    
    async def keypress_sound(self):
        """Keypress feedback - very short beep"""
        if self.simulation_mode:
            print("🎵 KEYPRESS")
            return
        
        await self.async_beep(1500, 0.03, 0.3)
    
    async def startup_sound(self):
        """System startup sound sequence"""
        if self.simulation_mode:
            print("🎵 STARTUP SOUND: Rising sweep + confirmation")
            await asyncio.sleep(2.0)
            return
        
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
        if self.simulation_mode:
            print(f"🚨 ALARM SOUND for {duration}s")
            await asyncio.sleep(duration)
            return
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            await self.async_beep(2000, 0.5, 0.8)
            await asyncio.sleep(0.1)
            await self.async_beep(1500, 0.5, 0.8)
            await asyncio.sleep(0.1)
    
    async def melody_sequence(self, notes: list, note_duration: float = 0.2):
        """
        Play a melody sequence
        
        Args:
            notes: List of frequencies (Hz) to play
            note_duration: Duration of each note in seconds
        """
        if self.simulation_mode:
            print(f"🎼 MELODY: {len(notes)} notes at {note_duration}s each")
            await asyncio.sleep(len(notes) * note_duration)
            return
        
        for frequency in notes:
            if frequency > 0:  # 0 = rest/pause
                await self.async_beep(frequency, note_duration * 0.8)
            await asyncio.sleep(note_duration)
    
    async def notification_sound(self, priority: str = "normal"):
        """
        Notification sound based on priority level
        
        Args:
            priority: "low", "normal", "high", "urgent"
        """
        if self.simulation_mode:
            print(f"🔔 NOTIFICATION: {priority.upper()} priority")
            await asyncio.sleep(0.5)
            return
        
        patterns = {
            "low": [(800, 0.1)],
            "normal": [(1000, 0.15), (1200, 0.15)],
            "high": [(1200, 0.1), (1000, 0.1), (1200, 0.1)],
            "urgent": [(1500, 0.1), (1000, 0.1)] * 3
        }
        
        pattern = patterns.get(priority, patterns["normal"])
        
        for freq, duration in pattern:
            await self.async_beep(freq, duration)
            await asyncio.sleep(0.05)
    
    async def door_sound(self, action: str):
        """
        Door-specific sound feedback
        
        Args:
            action: "unlock", "lock", "open", "close", "timeout"
        """
        if self.simulation_mode:
            print(f"🚪 DOOR SOUND: {action.upper()}")
            await asyncio.sleep(0.3)
            return
        
        sounds = {
            "unlock": [(1000, 0.1), (1200, 0.2)],
            "lock": [(1200, 0.1), (1000, 0.2)],
            "open": [(800, 0.1), (1000, 0.1), (1200, 0.1)],
            "close": [(1200, 0.1), (1000, 0.1), (800, 0.1)],
            "timeout": [(1500, 0.2), (1000, 0.2)] * 2
        }
        
        pattern = sounds.get(action, [(1000, 0.1)])
        
        for freq, duration in pattern:
            await self.async_beep(freq, duration)
            await asyncio.sleep(0.05)
    
    async def authentication_sound(self, result: str):
        """
        Authentication-specific sound feedback
        
        Args:
            result: "granted", "denied", "timeout", "processing"
        """
        if result == "granted":
            await self.success_sound()
        elif result == "denied":
            await self.error_sound()
        elif result == "timeout":
            await self.warning_sound()
        elif result == "processing":
            await self.processing_sound()
        else:
            await self.notification_sound("normal")
    
    async def play_musical_note(self, note: str, octave: int = 4, duration: float = 0.5):
        """
        Play a musical note
        
        Args:
            note: Musical note (C, D, E, F, G, A, B)
            octave: Octave number (1-8)
            duration: Note duration in seconds
        """
        # Note frequencies for octave 4
        note_frequencies = {
            'C': 261.63, 'D': 293.66, 'E': 329.63, 'F': 349.23,
            'G': 392.00, 'A': 440.00, 'B': 493.88
        }
        
        if note.upper() not in note_frequencies:
            print(f"⚠️  Unknown note: {note}")
            return
        
        # Calculate frequency for the specified octave
        base_freq = note_frequencies[note.upper()]
        frequency = int(base_freq * (2 ** (octave - 4)))
        
        if self.simulation_mode:
            print(f"🎵 Musical note: {note.upper()}{octave} ({frequency}Hz) for {duration}s")
            await asyncio.sleep(duration)
            return
        
        await self.async_beep(frequency, duration)
    
    async def volume_test(self):
        """Test different volume levels"""
        if self.simulation_mode:
            print("🔊 VOLUME TEST: Testing different volume levels")
            await asyncio.sleep(3.0)
            return
        
        print("Testing volume levels...")
        volumes = [0.2, 0.4, 0.6, 0.8, 1.0]
        
        for vol in volumes:
            print(f"Volume: {vol:.1%}")
            await self.async_beep(1000, 0.3, vol)
            await asyncio.sleep(0.2)
    
    async def frequency_test(self):
        """Test different frequencies"""
        if self.simulation_mode:
            print("🎵 FREQUENCY TEST: Testing frequency range")
            await asyncio.sleep(3.0)
            return
        
        print("Testing frequency range...")
        frequencies = [200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000]
        
        for freq in frequencies:
            print(f"Frequency: {freq}Hz")
            await self.async_beep(freq, 0.2)
            await asyncio.sleep(0.1)
    
    def set_volume(self, volume: float):
        """Set default volume level"""
        self.volume = max(0.0, min(1.0, volume))
        if self.simulation_mode:
            print(f"🔊 Volume set to {self.volume:.1%}")
    
    def get_status(self) -> dict:
        """Get buzzer status"""
        return {
            "simulation_mode": self.simulation_mode,
            "pin": self.buzzer_pin,
            "volume": self.volume,
            "available": GPIO_AVAILABLE
        }
    
    def cleanup(self):
        """Clean up PWM and GPIO resources"""
        if not self.simulation_mode and GPIO_AVAILABLE and self.pwm:
            try:
                self.pwm.stop()
                GPIO.setup(self.buzzer_pin, GPIO.IN)
                GPIO.cleanup()
            except Exception as e:
                print(f"⚠️  Buzzer GPIO cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass

# Musical scales and melodies
MUSICAL_SCALES = {
    "c_major": ["C", "D", "E", "F", "G", "A", "B"],
    "happy_birthday": [
        ("C", 4, 0.5), ("C", 4, 0.5), ("D", 4, 1.0), ("C", 4, 1.0),
        ("F", 4, 1.0), ("E", 4, 2.0)
    ]
}

# CLI testing interface
async def main():
    """CLI interface for buzzer testing"""
    print("🔊 Buzzer Controller Test")
    print("=" * 30)
    
    buzzer = BuzzerController()
    
    try:
        # Test basic sounds
        print("Testing basic beep...")
        await buzzer.async_beep(1000, 0.5)
        await asyncio.sleep(0.5)
        
        # Test system sounds
        print("Testing system sounds...")
        await buzzer.startup_sound()
        await asyncio.sleep(1)
        
        await buzzer.success_sound()
        await asyncio.sleep(1)
        
        await buzzer.error_sound()
        await asyncio.sleep(1)
        
        await buzzer.warning_sound()
        await asyncio.sleep(1)
        
        # Test authentication sounds
        print("Testing authentication sounds...")
        await buzzer.authentication_sound("granted")
        await asyncio.sleep(1)
        
        await buzzer.authentication_sound("denied")
        await asyncio.sleep(1)
        
        # Test door sounds
        print("Testing door sounds...")
        await buzzer.door_sound("unlock")
        await asyncio.sleep(0.5)
        
        await buzzer.door_sound("open")
        await asyncio.sleep(0.5)
        
        await buzzer.door_sound("close")
        await asyncio.sleep(0.5)
        
        await buzzer.door_sound("lock")
        await asyncio.sleep(1)
        
        # Test notifications
        print("Testing notification priorities...")
        for priority in ["low", "normal", "high", "urgent"]:
            print(f"Priority: {priority}")
            await buzzer.notification_sound(priority)
            await asyncio.sleep(1)
        
        # Test volume levels
        print("Testing volume levels...")
        await buzzer.volume_test()
        
        # Test frequency range
        print("Testing frequency range...")
        await buzzer.frequency_test()
        
        print("✅ Buzzer test completed")
        
    except KeyboardInterrupt:
        print("\n👋 Buzzer test stopped")
    finally:
        buzzer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())