# 🏠 Smart Locker System v2.0

## Overview

The Smart Locker System v2.0 is a comprehensive security solution that combines voice recognition, PIN verification, and hardware control for secure access management. Built for Raspberry Pi 4, this system provides dual-factor authentication with enterprise-grade security features.

## 🚀 Features

### Core Authentication
- **🎤 Voice Recognition**: ECAPA-TDNN neural networks via SpeechBrain
- **🔢 PIN Verification**: Secure PIN authentication with bcrypt hashing
- **🔀 Dual-Factor Auth**: Voice + PIN combination for enhanced security
- **📊 GMM Scoring**: Gaussian Mixture Models as secondary voice indicators

### Hardware Integration
- **⌨️ 4x4 Matrix Keypad**: Physical PIN entry interface
- **💡 RGB LED Status**: Visual feedback system
- **🔊 Buzzer Audio**: Audio feedback and alerts
- **🔒 Solenoid Lock**: Electronic lock control
- **🚪 Door Sensor**: Magnetic door position detection

### Smart Features
- **🚨 Emergency Unlock**: Multiple emergency access codes
- **👨‍💼 Admin Mode**: Administrative access and control
- **🎤 Voice Trigger**: Voice-activated authentication mode
- **⏰ Auto-Lock**: Automatic locking after timeout
- **📱 Keypad Input**: Comprehensive input handling with special patterns

### Security
- **🔐 Secure PIN Storage**: bcrypt password hashing
- **🚫 Lockout Protection**: Failed attempt protection
- **📋 Access Logging**: Comprehensive audit trail
- **🛡️ Role-Based Access**: User and admin role management

### Administration
- **🌐 Web Interface**: Streamlit-based admin dashboard
- **📊 Real-time Monitoring**: System status and metrics
- **👥 User Management**: Add, modify, delete users
- **⚙️ Configuration**: Dynamic system configuration
- **🔍 Diagnostics**: System health monitoring

## 📋 System Requirements

### Hardware Requirements
- **Raspberry Pi 4 Model B** (4GB+ RAM recommended)
- **MicroSD Card** (32GB+ Class 10)
- **USB Microphone** or **USB Audio Interface**
- **4x4 Matrix Keypad**
- **RGB LED Strip** (WS2812B/NeoPixel)
- **Active Buzzer** (5V)
- **12V Solenoid Lock**
- **Magnetic Door Sensor**
- **Relay Module** (for solenoid control)
- **Breadboard/PCB** for connections
- **Jumper Wires**
- **Power Supply** (5V/3A for Pi, 12V for solenoid)

### Software Requirements
- **Raspberry Pi OS** (Bookworm or newer)
- **Python 3.9+**
- **GPIO Libraries** (RPi.GPIO, gpiozero)
- **Audio Libraries** (portaudio, alsa)

## 🔧 Installation

### Automatic Installation (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/smart-locker-v2.git
   cd smart-locker-v2
   ```

2. **Run deployment script**:
   ```bash
   sudo python3 deploy_raspberry_pi.py deploy
   ```

3. **Start the system**:
   ```bash
   /opt/smart_locker/start_system.sh
   ```

### Manual Installation

1. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv python3-dev \
                       portaudio19-dev build-essential git alsa-utils \
                       pulseaudio i2c-tools raspi-gpio
   ```

2. **Enable GPIO interfaces**:
   ```bash
   sudo raspi-config nonint do_i2c 0
   sudo raspi-config nonint do_spi 0
   ```

3. **Create installation directory**:
   ```bash
   sudo mkdir -p /opt/smart_locker
   sudo chown pi:pi /opt/smart_locker
   ```

4. **Copy application files**:
   ```bash
   cp -r * /opt/smart_locker/
   cd /opt/smart_locker
   ```

5. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install RPi.GPIO adafruit-circuitpython-neopixel
   ```

6. **Configure services** (see deployment script for details)

## 🔌 Hardware Wiring

### GPIO Pin Assignments
```
# Keypad (4x4 Matrix)
ROW_PINS = [18, 23, 24, 25]    # GPIO pins for keypad rows
COL_PINS = [4, 17, 27, 22]     # GPIO pins for keypad columns

# RGB LED
LED_PIN = 12                    # GPIO pin for WS2812B LED strip
LED_COUNT = 8                   # Number of LEDs

# Buzzer
BUZZER_PIN = 13                 # GPIO pin for buzzer

# Solenoid Lock
SOLENOID_LOCK_PIN = 16          # GPIO pin for solenoid relay

# Door Sensor
DOOR_SENSOR_PIN = 26            # GPIO pin for magnetic door sensor
```

### Wiring Diagram
```
Raspberry Pi 4          Components
┌─────────────┐        
│             │        ┌─────────────┐
│ GPIO 18     ├────────┤ Keypad Row1 │
│ GPIO 23     ├────────┤ Keypad Row2 │
│ GPIO 24     ├────────┤ Keypad Row3 │
│ GPIO 25     ├────────┤ Keypad Row4 │
│ GPIO 4      ├────────┤ Keypad Col1 │
│ GPIO 17     ├────────┤ Keypad Col2 │
│ GPIO 27     ├────────┤ Keypad Col3 │
│ GPIO 22     ├────────┤ Keypad Col4 │
│             │        └─────────────┘
│ GPIO 12     ├────────┐ RGB LED Data
│ GPIO 13     ├────────┐ Buzzer +
│ GPIO 16     ├────────┐ Relay In
│ GPIO 26     ├────────┐ Door Sensor
│ 5V          ├────────┐ VCC (LED, Buzzer)
│ GND         ├────────┐ GND (All)
└─────────────┘        
```

## 🎯 Usage

### Initial Setup

1. **Start the system**:
   ```bash
   /opt/smart_locker/start_system.sh
   ```

2. **Access admin interface**:
   - Open browser to `http://<raspberry-pi-ip>:8501`
   - Default admin PIN: `admin123` (change immediately)

3. **Add users**:
   - Use admin interface to add users
   - Set PINs and enroll voice samples

### Normal Operation

#### Voice + PIN Authentication
1. Press `*V*` on keypad to trigger voice mode
2. Speak clearly when prompted (3-second recording)
3. If voice recognized, enter your PIN
4. Press `#` to submit
5. Door unlocks on successful authentication

#### PIN-Only Authentication
1. Enter your 4-8 digit PIN
2. Press `#` to submit
3. Door unlocks if PIN is correct

#### Emergency Access
- Enter emergency code: `*911*` or `#999#`
- Door unlocks immediately
- Event logged for security review

#### Admin Access
- Enter admin code: `*123*` or `#456#`
- Enter admin PIN when prompted
- Access admin functions via keypad

### Keypad Commands

| Command | Function |
|---------|----------|
| `*V*` | Activate voice recognition |
| `*911*` | Emergency unlock |
| `#999#` | Alternative emergency unlock |
| `*123*` | Admin mode activation |
| `#456#` | Alternative admin mode |
| `**` | Force emergency unlock |
| `##` | Force lock |
| `00` | Clear current input |
| `99` | Show system status |
| `A` | Admin functions |
| `B` | Backspace |
| `C` | Clear input |
| `D` | Emergency functions |

## 🔧 Configuration

### System Configuration
Edit `/opt/smart_locker/config/smart_locker_config.json`:

```json
{
  "voice_timeout": 10.0,
  "pin_timeout": 30.0,
  "access_duration": 30.0,
  "max_auth_attempts": 3,
  "voice_threshold": 0.75,
  "gmm_enabled": true,
  "emergency_codes": ["*911*", "#999#"],
  "admin_codes": ["*123*", "#456#"],
  "hardware_config": {
    "led_brightness": 0.8,
    "buzzer_volume": 0.7,
    "door_timeout": 300
  }
}
```

### Audio Configuration
For USB microphone setup:
```bash
# List audio devices
arecord -l

# Test microphone
arecord -D plughw:1,0 -d 5 test.wav
aplay test.wav
```

## 🌐 Admin Interface

### Dashboard Features
- **📊 Real-time Metrics**: System status, access counts, lock state
- **📈 Analytics**: Access patterns, authentication methods
- **📋 Recent Activity**: Live activity feed

### User Management
- **➕ Add Users**: Create new user accounts
- **🔑 PIN Management**: Set/reset user PINs
- **🎤 Voice Enrollment**: Manage voice profiles
- **🚫 User Control**: Enable/disable accounts

### System Control
- **🔓 Emergency Unlock**: Remote emergency access
- **🔒 Force Lock**: Remote lock activation
- **🔄 System Restart**: Restart system services
- **⚙️ Configuration**: Dynamic system settings

### Security Monitoring
- **📋 Access Logs**: Detailed access history
- **🚨 Security Events**: Failed attempts, alerts
- **🔍 Audit Trail**: Complete system audit

## 🧪 Testing

### Unit Tests
```bash
cd /opt/smart_locker
source venv/bin/activate

# Run PIN system tests
python test_pin_system.py

# Run integration tests
python test_smart_locker_integration.py --auto
```

### Manual Testing
```bash
# Test hardware controllers
python test_smart_locker_integration.py --manual

# Test individual components
python -m hardware.keypad_controller
python -m hardware.led_controller
python -m hardware.buzzer_controller
python -m hardware.lock_controller
```

## 🚨 Troubleshooting

### Common Issues

#### Voice Recognition Not Working
```bash
# Check microphone
arecord -l
arecord -D plughw:1,0 -d 3 test.wav

# Check audio permissions
sudo usermod -a -G audio pi

# Restart audio service
sudo systemctl restart alsa-state
```

#### GPIO Permission Errors
```bash
# Add user to gpio group
sudo usermod -a -G gpio pi

# Reboot required
sudo reboot
```

#### Service Not Starting
```bash
# Check service status
systemctl status smart-locker
journalctl -u smart-locker -f

# Check logs
tail -f /opt/smart_locker/logs/smart_locker.log
```

#### Admin Interface Not Accessible
```bash
# Check service
systemctl status smart-locker-admin

# Check firewall
sudo ufw status

# Check port binding
netstat -tlnp | grep 8501
```

### Log Files
- System logs: `/opt/smart_locker/logs/smart_locker.log`
- Service logs: `journalctl -u smart-locker`
- Admin logs: `journalctl -u smart-locker-admin`

## 🔒 Security Considerations

### Best Practices
1. **Change default admin PIN** immediately after installation
2. **Use strong PINs** (6+ digits, avoid patterns)
3. **Regular backup** user data and configurations
4. **Monitor access logs** for suspicious activity
5. **Update system** regularly for security patches
6. **Network security** - use firewall, VPN for remote access

### Security Features
- **PIN encryption** using bcrypt hashing
- **Failed attempt lockout** prevents brute force
- **Access logging** provides complete audit trail
- **Emergency codes** for security override
- **Admin separation** from user access

## 📚 API Reference

### Main Controller
```python
from main_controller import SmartLockerController

# Initialize system
controller = SmartLockerController(simulation_mode=False)
await controller.initialize()

# Get system status
status = controller.get_system_status()

# Shutdown system
await controller.shutdown()
```

### Hardware Controllers
```python
from hardware.keypad_controller import KeypadController
from hardware.led_controller import LEDController
from hardware.buzzer_controller import BuzzerController
from hardware.lock_controller import LockController

# Initialize hardware
keypad = KeypadController()
led = LEDController()
buzzer = BuzzerController()
lock = LockController()

# Use hardware
await led.set_status("ready")
await buzzer.success_sound()
await lock.unlock()
```

### Authentication
```python
from auth.pin_verification import PINVerifier
from auth.access_control import AccessController

# PIN verification
pin_verifier = PINVerifier()
await pin_verifier.set_user_pin("user123", "1234")
result = await pin_verifier.verify_pin("user123", "1234")

# Access control
access_controller = AccessController(pin_verifier)
result = await access_controller.authenticate_user("user123", "1234", "pin")
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Authors

- **TA Voice Recognition System v2** - Initial work and Smart Locker transformation

## 🙏 Acknowledgments

- **SpeechBrain** for ECAPA-TDNN voice recognition models
- **Raspberry Pi Foundation** for the excellent hardware platform
- **Streamlit** for the admin interface framework
- **scikit-learn** for GMM implementation

## 📞 Support

For support and questions:
- 📧 Email: support@smartlocker.local
- 📖 Documentation: [Wiki](https://github.com/your-repo/smart-locker-v2/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/smart-locker-v2/issues)

## 🗓️ Changelog

### v2.0.0 (2024-01-15)
- ✨ Complete system transformation from voice recognition to smart locker
- 🔐 Dual-factor authentication (Voice + PIN)
- 🎯 Hardware integration with Raspberry Pi 4
- 🌐 Streamlit admin interface
- 📊 GMM secondary voice indicators
- 🚨 Emergency and admin access modes
- 🔒 Enterprise-grade security features
- 📋 Comprehensive logging and monitoring
- 🚀 Automated deployment system

### v1.0.0 (Previous)
- 🎤 Basic voice recognition system
- 📱 Streamlit interface for voice enrollment
- 🔍 Speaker identification and verification

---

**🏠 Smart Locker System v2.0** - Secure. Intelligent. Reliable.