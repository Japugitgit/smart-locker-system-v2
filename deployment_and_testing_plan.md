# Deployment & Testing Plan - Smart Locker System

## 🚀 Deployment Architecture

```
Production Deployment on Raspberry Pi 4:

┌─────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI 4 SETUP                     │
│                                                             │
│ ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│ │   System Level  │  │ Application     │  │   Hardware   │ │
│ │                 │  │     Level       │  │    Level     │ │
│ │ • Raspbian OS   │  │ • Python 3.9+  │  │ • GPIO Pins  │ │
│ │ • systemd       │  │ • Virtual Env   │  │ • Keypad 4x4 │ │
│ │ • Audio drivers │  │ • Smart Locker  │  │ • Solenoid   │ │
│ │ • GPIO access   │  │ • Streamlit     │  │ • LEDs       │ │
│ │ • SSH/VNC       │  │ • Dependencies  │  │ • Buzzer     │ │
│ └─────────────────┘  └─────────────────┘  │ • USB Mic    │ │
│                                           └──────────────┘ │
└─────────────────────────────────────────────────────────────┘

Network Configuration:
┌─────────────────────────────────────────────────────────────┐
│ Router/WiFi [192.168.1.1] ←→ Raspberry Pi [192.168.1.100]  │
│                                      ↓                      │
│ Admin Access: http://192.168.1.100:8501 (Streamlit)        │
│ SSH Access:   ssh pi@192.168.1.100                        │
│ VNC Access:   vnc://192.168.1.100:5901                    │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Installation & Setup Guide

### 1. Raspberry Pi 4 Preparation

```bash
# === INITIAL SYSTEM SETUP ===

# 1. Flash Raspberry Pi OS (64-bit recommended)
# Download: https://www.raspberrypi.org/software/
# Flash to SD card (32GB+ recommended)

# 2. Enable SSH and configure WiFi
sudo raspi-config
# - Interface Options > SSH > Enable
# - Network Options > WiFi > Configure

# 3. Update system
sudo apt update && sudo apt upgrade -y

# 4. Install required system packages
sudo apt install -y \
    python3-pip python3-venv python3-dev \
    git curl wget htop nano \
    alsa-utils pulseaudio \
    build-essential cmake \
    libportaudio2 libportaudiocpp0 portaudio19-dev \
    libffi-dev libssl-dev \
    sqlite3 libsqlite3-dev

# 5. Configure audio system
sudo usermod -a -G audio pi
sudo usermod -a -G gpio pi

# 6. Install GPIO libraries
sudo apt install -y python3-rpi.gpio

# 7. Enable GPIO and audio interfaces
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_camera 0
```

### 2. Application Deployment

```bash
# === APPLICATION SETUP ===

# 1. Create application directory
sudo mkdir -p /opt/smart-locker
sudo chown pi:pi /opt/smart-locker
cd /opt/smart-locker

# 2. Clone/copy application code
git clone <repository_url> .
# OR: Copy files from development system

# 3. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install Python dependencies
pip install --upgrade pip
pip install -r requirements_rpi.txt

# 5. Create necessary directories
mkdir -p logs data data/gmm_models config

# 6. Set up configuration files
cp config/system_config.example.json config/system_config.json
cp config/security_config.example.json config/security_config.json

# 7. Set proper permissions
chmod +x start_locker.py
chmod +x scripts/*.sh
sudo chown -R pi:pi /opt/smart-locker

# 8. Configure environment variables
echo 'export LOCKER_ADMIN_PIN="your_secure_admin_pin"' >> ~/.bashrc
echo 'export LOCKER_HOME="/opt/smart-locker"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Hardware Setup & Wiring

```bash
# === HARDWARE WIRING DIAGRAM ===

# GPIO Pin Assignments (BCM numbering):
# ┌─────────────────────────────────────────┐
# │ COMPONENT        │ GPIO PIN │ PHYSICAL │
# ├─────────────────────────────────────────┤
# │ Keypad Row 1     │    18    │    12    │
# │ Keypad Row 2     │    19    │    35    │
# │ Keypad Row 3     │    20    │    38    │
# │ Keypad Row 4     │    21    │    40    │
# │ Keypad Col 1     │    12    │    32    │
# │ Keypad Col 2     │    16    │    36    │
# │ Keypad Col 3     │    26    │    37    │
# │ Keypad Col 4     │    13    │    33    │
# ├─────────────────────────────────────────┤
# │ Solenoid Relay   │    23    │    16    │
# │ Door Sensor      │    27    │    13    │
# ├─────────────────────────────────────────┤
# │ LED Red          │    25    │    22    │
# │ LED Green        │    24    │    18    │
# │ LED Blue         │    22    │    15    │
# │ Buzzer           │     4    │     7    │
# └─────────────────────────────────────────┘

# Test GPIO setup
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
print('GPIO setup successful')
GPIO.cleanup()
"
```

### 4. System Service Configuration

```bash
# === SYSTEMD SERVICE SETUP ===

# 1. Create systemd service file
sudo nano /etc/systemd/system/smart-locker.service

# Service file content:
# [Unit]
# Description=Smart Locker Voice Recognition System
# After=network.target sound.target multi-user.target
# Wants=network.target
# 
# [Service]
# Type=simple
# User=pi
# Group=pi
# WorkingDirectory=/opt/smart-locker
# Environment=PATH=/opt/smart-locker/venv/bin
# Environment=PYTHONPATH=/opt/smart-locker
# EnvironmentFile=/opt/smart-locker/.env
# ExecStart=/opt/smart-locker/venv/bin/python /opt/smart-locker/start_locker.py
# Restart=always
# RestartSec=10
# StandardOutput=journal
# StandardError=journal
# SyslogIdentifier=smart-locker
# 
# [Install]
# WantedBy=multi-user.target

# 2. Create environment file
cat > /opt/smart-locker/.env << EOF
LOCKER_ADMIN_PIN=your_secure_admin_pin
LOCKER_HOME=/opt/smart-locker
PYTHONPATH=/opt/smart-locker
PATH=/opt/smart-locker/venv/bin:/usr/local/bin:/usr/bin:/bin
EOF

# 3. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable smart-locker.service
sudo systemctl start smart-locker.service

# 4. Check service status
sudo systemctl status smart-locker.service
```

### 5. Streamlit Admin Interface Service

```bash
# === STREAMLIT ADMIN INTERFACE ===

# 1. Create Streamlit service
sudo nano /etc/systemd/system/smart-locker-admin.service

# Service content:
# [Unit]
# Description=Smart Locker Admin Interface
# After=network.target smart-locker.service
# Requires=smart-locker.service
# 
# [Service]
# Type=simple
# User=pi
# Group=pi
# WorkingDirectory=/opt/smart-locker
# Environment=PATH=/opt/smart-locker/venv/bin
# ExecStart=/opt/smart-locker/venv/bin/streamlit run admin_app.py --server.port=8501 --server.address=0.0.0.0
# Restart=always
# RestartSec=5
# 
# [Install]
# WantedBy=multi-user.target

# 2. Enable admin interface
sudo systemctl enable smart-locker-admin.service
sudo systemctl start smart-locker-admin.service
```

## 🧪 Testing Strategy

### 1. Unit Testing

```python
# === UNIT TESTS ===

# tests/test_pin_verification.py
import unittest
from auth.pin_verification import PINVerification

class TestPINVerification(unittest.TestCase):
    def setUp(self):
        self.pin_verifier = PINVerification()
    
    def test_hash_pin(self):
        """Test PIN hashing functionality"""
        pin = "1234"
        hashed = self.pin_verifier.hash_pin(pin)
        self.assertTrue(hashed.startswith('$2b$'))
    
    def test_verify_pin_success(self):
        """Test successful PIN verification"""
        user_id = "test_user"
        pin = "1234"
        
        # Set PIN
        self.pin_verifier.set_pin(user_id, pin)
        
        # Verify PIN
        success, reason = self.pin_verifier.verify_pin(user_id, pin)
        self.assertTrue(success)
        self.assertEqual(reason, "success")
    
    def test_verify_pin_failure(self):
        """Test failed PIN verification"""
        user_id = "test_user"
        correct_pin = "1234"
        wrong_pin = "5678"
        
        # Set PIN
        self.pin_verifier.set_pin(user_id, correct_pin)
        
        # Verify wrong PIN
        success, reason = self.pin_verifier.verify_pin(user_id, wrong_pin)
        self.assertFalse(success)
        self.assertEqual(reason, "wrong_pin")
    
    def test_lockout_policy(self):
        """Test user lockout after failed attempts"""
        user_id = "test_user"
        pin = "1234"
        wrong_pin = "0000"
        
        self.pin_verifier.set_pin(user_id, pin)
        
        # Fail 3 times to trigger lockout
        for _ in range(3):
            self.pin_verifier.verify_pin(user_id, wrong_pin)
        
        # Should be locked out now
        self.assertTrue(self.pin_verifier.is_user_locked_out(user_id))
        
        # Even correct PIN should fail during lockout
        success, reason = self.pin_verifier.verify_pin(user_id, pin)
        self.assertFalse(success)
        self.assertEqual(reason, "user_locked_out")

# tests/test_hardware_simulation.py
class TestHardwareSimulation(unittest.TestCase):
    """Test hardware controllers in simulation mode"""
    
    def test_keypad_simulation(self):
        """Test keypad input simulation"""
        pass
    
    def test_lock_simulation(self):
        """Test lock controller simulation"""
        pass
    
    def test_led_simulation(self):
        """Test LED controller simulation"""
        pass
```

### 2. Integration Testing

```python
# === INTEGRATION TESTS ===

# tests/test_authentication_flow.py
import asyncio
import unittest
from unittest.mock import Mock, patch

class TestAuthenticationFlow(unittest.TestCase):
    """Test complete authentication flow"""
    
    def setUp(self):
        # Mock hardware for testing
        self.mock_keypad = Mock()
        self.mock_lock = Mock()
        self.mock_leds = Mock()
        self.mock_buzzer = Mock()
    
    @patch('main_controller.KeypadController')
    @patch('main_controller.LockController')
    async def test_voice_pin_flow_success(self, mock_lock_cls, mock_keypad_cls):
        """Test successful voice + PIN authentication"""
        
        # Setup mocks
        mock_keypad_cls.return_value = self.mock_keypad
        mock_lock_cls.return_value = self.mock_lock
        
        # Simulate voice recognition success
        with patch('core.speaker_recognition.SpeakerRecognition') as mock_voice:
            mock_voice.return_value.identify_speaker.return_value = {
                'user_id': 'test_user',
                'confidence': 0.85
            }
            
            # Simulate PIN input
            self.mock_keypad.get_pin_input.return_value = "1234"
            
            # Test authentication flow
            from main_controller import SmartLockerController
            controller = SmartLockerController()
            
            # This would test the complete flow
            # result = await controller.start_voice_recognition_flow()
            # self.assertTrue(result['success'])
    
    async def test_voice_pin_flow_failure(self):
        """Test failed authentication scenarios"""
        pass
    
    async def test_admin_mode_flow(self):
        """Test admin mode functionality"""
        pass
    
    async def test_emergency_unlock_flow(self):
        """Test emergency unlock functionality"""
        pass
```

### 3. Hardware Testing Scripts

```python
# === HARDWARE TESTING ===

# scripts/test_hardware.py
#!/usr/bin/env python3
"""
Hardware component testing script
Tests each hardware component individually
"""

import asyncio
import time
import RPi.GPIO as GPIO
from hardware.keypad_controller import KeypadController
from hardware.lock_controller import LockController
from hardware.led_controller import LEDController
from hardware.buzzer_controller import BuzzerController

async def test_keypad():
    """Test keypad functionality"""
    print("🔢 Testing Keypad...")
    keypad = KeypadController()
    
    print("Press any key on the keypad (timeout: 10s)")
    key = await keypad.wait_for_key(timeout=10.0)
    
    if key:
        print(f"✅ Key pressed: {key}")
    else:
        print("❌ No key pressed or timeout")
    
    keypad.cleanup()

async def test_leds():
    """Test LED functionality"""
    print("💡 Testing LEDs...")
    leds = LEDController()
    
    # Test each color
    colors = ['red', 'green', 'blue']
    for color in colors:
        print(f"Testing {color} LED...")
        leds.set_led(color, 1.0)
        await asyncio.sleep(1.0)
        leds.set_led(color, 0.0)
    
    # Test status patterns
    statuses = ['ready', 'processing', 'success', 'error']
    for status in statuses:
        print(f"Testing {status} status...")
        leds.set_status(status)
        await asyncio.sleep(2.0)
    
    leds.set_status('off')
    leds.cleanup()

async def test_buzzer():
    """Test buzzer functionality"""
    print("🔊 Testing Buzzer...")
    buzzer = BuzzerController()
    
    # Test different sounds
    print("Testing startup sound...")
    await buzzer.startup_sound()
    
    await asyncio.sleep(1.0)
    
    print("Testing success sound...")
    await buzzer.success_sound()
    
    await asyncio.sleep(1.0)
    
    print("Testing error sound...")
    await buzzer.error_sound()
    
    buzzer.cleanup()

async def test_lock():
    """Test lock controller"""
    print("🔒 Testing Lock Controller...")
    
    def status_callback(event, data):
        print(f"Lock event: {event} - {data}")
    
    lock = LockController(status_callback=status_callback)
    
    print("Testing unlock...")
    await lock.unlock_door(duration=3.0)
    
    print("Waiting for auto-lock...")
    await asyncio.sleep(4.0)
    
    print("Testing door sensor...")
    door_status = lock.get_door_status()
    print(f"Door status: {door_status}")
    
    lock.cleanup()

async def main():
    """Main hardware test function"""
    print("🧪 Smart Locker Hardware Test Suite")
    print("=" * 50)
    
    try:
        await test_leds()
        await asyncio.sleep(1.0)
        
        await test_buzzer()
        await asyncio.sleep(1.0)
        
        await test_keypad()
        await asyncio.sleep(1.0)
        
        await test_lock()
        
        print("\n✅ All hardware tests completed!")
        
    except Exception as e:
        print(f"\n❌ Hardware test failed: {str(e)}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Performance Testing

```python
# === PERFORMANCE TESTS ===

# scripts/performance_test.py
import time
import statistics
from core.speaker_recognition import SpeakerRecognition
from auth.pin_verification import PINVerification

def test_voice_recognition_performance():
    """Test voice recognition speed"""
    print("⚡ Testing Voice Recognition Performance...")
    
    speaker_rec = SpeakerRecognition()
    times = []
    
    # Test with sample audio files
    for i in range(10):
        start_time = time.time()
        # result = speaker_rec.identify_speaker(sample_audio)
        end_time = time.time()
        
        times.append(end_time - start_time)
    
    avg_time = statistics.mean(times)
    print(f"Average recognition time: {avg_time:.3f}s")
    print(f"Min time: {min(times):.3f}s")
    print(f"Max time: {max(times):.3f}s")

def test_pin_verification_performance():
    """Test PIN verification speed"""
    print("⚡ Testing PIN Verification Performance...")
    
    pin_verifier = PINVerification()
    times = []
    
    # Setup test user
    pin_verifier.set_pin("test_user", "1234")
    
    for i in range(100):
        start_time = time.time()
        pin_verifier.verify_pin("test_user", "1234")
        end_time = time.time()
        
        times.append(end_time - start_time)
    
    avg_time = statistics.mean(times)
    print(f"Average PIN verification time: {avg_time*1000:.3f}ms")

def test_system_memory_usage():
    """Test system memory usage"""
    import psutil
    
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"CPU usage: {process.cpu_percent():.2f}%")
```

## 📊 Monitoring & Maintenance

### 1. System Monitoring

```bash
# === MONITORING SETUP ===

# 1. Log monitoring script
# scripts/monitor_logs.sh
#!/bin/bash
echo "Smart Locker System Monitoring"
echo "=============================="

echo "System Service Status:"
systemctl status smart-locker.service --no-pager

echo -e "\nAdmin Interface Status:"
systemctl status smart-locker-admin.service --no-pager

echo -e "\nRecent System Logs:"
journalctl -u smart-locker.service -n 20 --no-pager

echo -e "\nSystem Resources:"
echo "CPU: $(vcgencmd measure_temp)"
echo "Memory: $(free -h | grep Mem)"
echo "Disk: $(df -h / | tail -1)"

# 2. Health check script
# scripts/health_check.py
import requests
import json
import sys

def check_admin_interface():
    """Check if admin interface is accessible"""
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_hardware_status():
    """Check hardware component status"""
    try:
        # Test GPIO access
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
        return True
    except:
        return False

def main():
    checks = {
        "admin_interface": check_admin_interface(),
        "hardware": check_hardware_status()
    }
    
    all_good = all(checks.values())
    
    print(json.dumps({
        "timestamp": time.time(),
        "status": "healthy" if all_good else "issues",
        "checks": checks
    }))
    
    sys.exit(0 if all_good else 1)

if __name__ == "__main__":
    main()
```

### 2. Backup & Recovery

```bash
# === BACKUP STRATEGY ===

# 1. Data backup script
# scripts/backup_data.sh
#!/bin/bash

BACKUP_DIR="/opt/smart-locker/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="locker_backup_${DATE}.tar.gz"

mkdir -p $BACKUP_DIR

echo "Creating backup: $BACKUP_FILE"

tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    data/users.json \
    data/access_logs.json \
    data/gmm_models/ \
    config/ \
    logs/

echo "Backup created successfully"

# Keep only last 7 days of backups
find $BACKUP_DIR -name "locker_backup_*.tar.gz" -mtime +7 -delete

# 2. Recovery script
# scripts/restore_backup.sh
#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Stopping services..."
sudo systemctl stop smart-locker.service
sudo systemctl stop smart-locker-admin.service

echo "Restoring from backup: $BACKUP_FILE"
tar -xzf "$BACKUP_FILE" -C /opt/smart-locker/

echo "Starting services..."
sudo systemctl start smart-locker.service
sudo systemctl start smart-locker-admin.service

echo "Recovery completed"
```

## 🎯 Deployment Checklist

### Pre-Deployment:
- [ ] Hardware components tested individually
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Security audit completed

### Deployment:
- [ ] Raspberry Pi OS configured
- [ ] Dependencies installed
- [ ] Application deployed
- [ ] Services configured and enabled
- [ ] Hardware properly wired
- [ ] Network configuration verified

### Post-Deployment:
- [ ] System services running
- [ ] Admin interface accessible
- [ ] Hardware components responding
- [ ] Audio system working
- [ ] Backup system configured
- [ ] Monitoring alerts setup

### Operational:
- [ ] User training completed
- [ ] Documentation provided
- [ ] Maintenance schedule established
- [ ] Support procedures defined

## 🔧 Troubleshooting Guide

### Common Issues:

1. **Audio not working**
   ```bash
   # Check audio devices
   arecord -l
   # Test microphone
   arecord -d 5 test.wav && aplay test.wav
   ```

2. **GPIO permissions**
   ```bash
   sudo usermod -a -G gpio pi
   sudo chmod 666 /dev/gpiomem
   ```

3. **Service not starting**
   ```bash
   journalctl -u smart-locker.service -f
   sudo systemctl daemon-reload
   ```

4. **Memory issues**
   ```bash
   # Increase swap space
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile  # CONF_SWAPSIZE=2048
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

Deployment plan ini memberikan roadmap lengkap untuk implementasi sistem Smart Locker pada Raspberry Pi 4 dengan testing komprehensif dan monitoring.