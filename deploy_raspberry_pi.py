#!/usr/bin/env python3
"""
Smart Locker Deployment Script for Raspberry Pi 4
Automates installation, configuration, and service setup
"""

import os
import sys
import subprocess
import json
import shutil
import argparse
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RaspberryPiDeployer:
    """Deployment manager for Raspberry Pi Smart Locker System"""
    
    def __init__(self, target_dir="/opt/smart_locker"):
        self.target_dir = Path(target_dir)
        self.service_name = "smart-locker"
        self.user = "pi"
        self.python_env = self.target_dir / "venv"
        
        # System requirements
        self.system_packages = [
            "python3",
            "python3-pip", 
            "python3-venv",
            "python3-dev",
            "portaudio19-dev",
            "build-essential",
            "git",
            "alsa-utils",
            "pulseaudio",
            "i2c-tools",
            "raspi-gpio"
        ]
        
        # Python packages for Raspberry Pi
        self.rpi_packages = [
            "RPi.GPIO",
            "adafruit-circuitpython-neopixel",
            "board",
            "digitalio"
        ]
    
    def run_command(self, cmd, check=True, shell=True):
        """Run shell command with logging"""
        logger.info(f"Executing: {cmd}")
        try:
            result = subprocess.run(
                cmd, 
                shell=shell, 
                check=check, 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                logger.debug(f"STDOUT: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            if e.stderr:
                logger.error(f"STDERR: {e.stderr}")
            raise
    
    def check_raspberry_pi(self):
        """Check if running on Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            if 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo:
                logger.info("✅ Raspberry Pi detected")
                return True
            else:
                logger.warning("⚠️  Not running on Raspberry Pi")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to detect Raspberry Pi: {e}")
            return False
    
    def install_system_packages(self):
        """Install required system packages"""
        logger.info("📦 Installing system packages...")
        
        # Update package list
        self.run_command("sudo apt update")
        
        # Install packages
        packages_str = " ".join(self.system_packages)
        self.run_command(f"sudo apt install -y {packages_str}")
        
        logger.info("✅ System packages installed")
    
    def enable_gpio_interfaces(self):
        """Enable GPIO, I2C, SPI interfaces"""
        logger.info("🔌 Enabling GPIO interfaces...")
        
        # Enable I2C
        self.run_command("sudo raspi-config nonint do_i2c 0")
        
        # Enable SPI
        self.run_command("sudo raspi-config nonint do_spi 0")
        
        # Add user to gpio group
        self.run_command(f"sudo usermod -a -G gpio {self.user}")
        
        logger.info("✅ GPIO interfaces enabled")
    
    def create_target_directory(self):
        """Create target installation directory"""
        logger.info(f"📁 Creating target directory: {self.target_dir}")
        
        # Create directory with proper permissions
        self.run_command(f"sudo mkdir -p {self.target_dir}")
        self.run_command(f"sudo chown -R {self.user}:{self.user} {self.target_dir}")
        
        logger.info("✅ Target directory created")
    
    def copy_application_files(self, source_dir="."):
        """Copy application files to target directory"""
        logger.info(f"📋 Copying application files from {source_dir}...")
        
        source_path = Path(source_dir)
        
        # Files and directories to copy
        items_to_copy = [
            "main_controller.py",
            "admin_interface.py", 
            "speaker_recognition.py",
            "voice_recorder.py",
            "gmm_speaker.py",
            "requirements.txt",
            "auth/",
            "hardware/",
            "config/",
            "pages/",
            "data/"
        ]
        
        for item in items_to_copy:
            source_item = source_path / item
            target_item = self.target_dir / item
            
            if source_item.exists():
                if source_item.is_dir():
                    shutil.copytree(source_item, target_item, dirs_exist_ok=True)
                else:
                    target_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_item, target_item)
                logger.info(f"  ✅ Copied {item}")
            else:
                logger.warning(f"  ⚠️  {item} not found, skipping")
        
        logger.info("✅ Application files copied")
    
    def create_python_environment(self):
        """Create Python virtual environment"""
        logger.info("🐍 Creating Python virtual environment...")
        
        # Create virtual environment
        self.run_command(f"python3 -m venv {self.python_env}")
        
        # Upgrade pip
        pip_cmd = f"{self.python_env}/bin/pip"
        self.run_command(f"{pip_cmd} install --upgrade pip")
        
        logger.info("✅ Python environment created")
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        logger.info("📚 Installing Python dependencies...")
        
        pip_cmd = f"{self.python_env}/bin/pip"
        
        # Install from requirements.txt
        requirements_file = self.target_dir / "requirements.txt"
        if requirements_file.exists():
            self.run_command(f"{pip_cmd} install -r {requirements_file}")
        
        # Install Raspberry Pi specific packages
        for package in self.rpi_packages:
            try:
                self.run_command(f"{pip_cmd} install {package}")
                logger.info(f"  ✅ Installed {package}")
            except subprocess.CalledProcessError:
                logger.warning(f"  ⚠️  Failed to install {package}, continuing...")
        
        logger.info("✅ Python dependencies installed")
    
    def create_systemd_service(self):
        """Create systemd service for auto-start"""
        logger.info("⚙️ Creating systemd service...")
        
        service_content = f"""[Unit]
Description=Smart Locker System
After=network.target
Wants=network.target

[Service]
Type=simple
User={self.user}
Group={self.user}
WorkingDirectory={self.target_dir}
Environment=PATH={self.python_env}/bin
ExecStart={self.python_env}/bin/python main_controller.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        # Write service file
        service_file = f"/etc/systemd/system/{self.service_name}.service"
        
        with open("/tmp/smart-locker.service", "w") as f:
            f.write(service_content)
        
        self.run_command(f"sudo mv /tmp/smart-locker.service {service_file}")
        self.run_command(f"sudo chmod 644 {service_file}")
        
        # Reload systemd and enable service
        self.run_command("sudo systemctl daemon-reload")
        self.run_command(f"sudo systemctl enable {self.service_name}")
        
        logger.info("✅ Systemd service created and enabled")
    
    def create_admin_service(self):
        """Create systemd service for admin interface"""
        logger.info("🌐 Creating admin interface service...")
        
        admin_service_content = f"""[Unit]
Description=Smart Locker Admin Interface
After=network.target
Wants=network.target

[Service]
Type=simple
User={self.user}
Group={self.user}
WorkingDirectory={self.target_dir}
Environment=PATH={self.python_env}/bin
ExecStart={self.python_env}/bin/streamlit run admin_interface.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        # Write admin service file
        admin_service_file = "/etc/systemd/system/smart-locker-admin.service"
        
        with open("/tmp/smart-locker-admin.service", "w") as f:
            f.write(admin_service_content)
        
        self.run_command(f"sudo mv /tmp/smart-locker-admin.service {admin_service_file}")
        self.run_command(f"sudo chmod 644 {admin_service_file}")
        
        # Enable admin service
        self.run_command("sudo systemctl enable smart-locker-admin")
        
        logger.info("✅ Admin interface service created and enabled")
    
    def configure_audio(self):
        """Configure audio for voice recognition"""
        logger.info("🔊 Configuring audio...")
        
        # Set default audio device
        asound_conf = """pcm.!default {
    type asym
    playback.pcm "plughw:0,0"
    capture.pcm "plughw:1,0"
}
ctl.!default {
    type hw
    card 0
}"""
        
        # Write ALSA configuration
        with open("/tmp/asound.conf", "w") as f:
            f.write(asound_conf)
        
        self.run_command("sudo mv /tmp/asound.conf /etc/asound.conf")
        
        # Add user to audio group
        self.run_command(f"sudo usermod -a -G audio {self.user}")
        
        logger.info("✅ Audio configured")
    
    def create_startup_script(self):
        """Create startup script"""
        logger.info("🚀 Creating startup script...")
        
        startup_script = f"""#!/bin/bash
# Smart Locker System Startup Script

set -e

echo "🏠 Starting Smart Locker System..."

# Check if system is ready
if systemctl is-active --quiet {self.service_name}; then
    echo "✅ Smart Locker service is running"
else
    echo "🔄 Starting Smart Locker service..."
    sudo systemctl start {self.service_name}
fi

if systemctl is-active --quiet smart-locker-admin; then
    echo "✅ Admin interface is running"
else
    echo "🔄 Starting Admin interface..."
    sudo systemctl start smart-locker-admin
fi

echo "📊 System Status:"
systemctl status {self.service_name} --no-pager -l
systemctl status smart-locker-admin --no-pager -l

echo ""
echo "🌐 Admin Interface: http://$(hostname -I | awk '{{print $1}}'):8501"
echo "🏠 Smart Locker System is ready!"
"""
        
        script_path = self.target_dir / "start_system.sh"
        with open(script_path, "w") as f:
            f.write(startup_script)
        
        self.run_command(f"chmod +x {script_path}")
        
        logger.info("✅ Startup script created")
    
    def create_backup_script(self):
        """Create backup script"""
        logger.info("💾 Creating backup script...")
        
        backup_script = f"""#!/bin/bash
# Smart Locker System Backup Script

BACKUP_DIR="/home/{self.user}/smart_locker_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/smart_locker_backup_$TIMESTAMP.tar.gz"

echo "💾 Creating backup: $BACKUP_FILE"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop services
sudo systemctl stop {self.service_name}
sudo systemctl stop smart-locker-admin

# Create backup
tar -czf "$BACKUP_FILE" -C {self.target_dir.parent} {self.target_dir.name}

# Start services
sudo systemctl start {self.service_name}
sudo systemctl start smart-locker-admin

# Clean old backups (keep last 7)
cd "$BACKUP_DIR"
ls -t *.tar.gz | tail -n +8 | xargs -r rm

echo "✅ Backup completed: $BACKUP_FILE"
"""
        
        backup_path = self.target_dir / "backup_system.sh"
        with open(backup_path, "w") as f:
            f.write(backup_script)
        
        self.run_command(f"chmod +x {backup_path}")
        
        # Add to crontab for daily backup
        cron_entry = f"0 2 * * * {backup_path} >> /var/log/smart_locker_backup.log 2>&1"
        self.run_command(f'(crontab -l 2>/dev/null; echo "{cron_entry}") | crontab -')
        
        logger.info("✅ Backup script created and scheduled")
    
    def configure_firewall(self):
        """Configure firewall for security"""
        logger.info("🔥 Configuring firewall...")
        
        try:
            # Install UFW if not present
            self.run_command("sudo apt install -y ufw")
            
            # Reset UFW
            self.run_command("sudo ufw --force reset")
            
            # Default policies
            self.run_command("sudo ufw default deny incoming")
            self.run_command("sudo ufw default allow outgoing")
            
            # Allow SSH
            self.run_command("sudo ufw allow ssh")
            
            # Allow admin interface
            self.run_command("sudo ufw allow 8501/tcp")
            
            # Enable firewall
            self.run_command("sudo ufw --force enable")
            
            logger.info("✅ Firewall configured")
            
        except Exception as e:
            logger.warning(f"⚠️  Firewall configuration failed: {e}")
    
    def generate_ssl_certificate(self):
        """Generate self-signed SSL certificate"""
        logger.info("🔒 Generating SSL certificate...")
        
        try:
            ssl_dir = self.target_dir / "ssl"
            ssl_dir.mkdir(exist_ok=True)
            
            # Generate private key
            self.run_command(f"openssl genrsa -out {ssl_dir}/private.key 2048")
            
            # Generate certificate
            self.run_command(f"""openssl req -new -x509 -key {ssl_dir}/private.key \
                -out {ssl_dir}/certificate.crt -days 365 \
                -subj "/C=US/ST=State/L=City/O=SmartLocker/CN=raspberrypi.local" """)
            
            # Set permissions
            self.run_command(f"chmod 600 {ssl_dir}/private.key")
            self.run_command(f"chmod 644 {ssl_dir}/certificate.crt")
            
            logger.info("✅ SSL certificate generated")
            
        except Exception as e:
            logger.warning(f"⚠️  SSL certificate generation failed: {e}")
    
    def deploy(self, source_dir=".", enable_ssl=False):
        """Run complete deployment"""
        logger.info("🚀 Starting Smart Locker deployment...")
        
        try:
            # Check environment
            if not self.check_raspberry_pi():
                response = input("Not on Raspberry Pi. Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Deployment cancelled")
                    return False
            
            # Installation steps
            self.install_system_packages()
            self.enable_gpio_interfaces()
            self.create_target_directory()
            self.copy_application_files(source_dir)
            self.create_python_environment()
            self.install_python_dependencies()
            self.configure_audio()
            self.create_systemd_service()
            self.create_admin_service()
            self.create_startup_script()
            self.create_backup_script()
            self.configure_firewall()
            
            if enable_ssl:
                self.generate_ssl_certificate()
            
            logger.info("✅ Deployment completed successfully!")
            logger.info(f"📁 Installation directory: {self.target_dir}")
            logger.info(f"🚀 Start system: {self.target_dir}/start_system.sh")
            logger.info("🌐 Admin interface will be available at: http://<raspberry-pi-ip>:8501")
            
            # Prompt to start services
            response = input("Start services now? (Y/n): ")
            if response.lower() != 'n':
                self.start_services()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            return False
    
    def start_services(self):
        """Start all services"""
        logger.info("🚀 Starting services...")
        
        try:
            self.run_command(f"sudo systemctl start {self.service_name}")
            self.run_command("sudo systemctl start smart-locker-admin")
            
            logger.info("✅ Services started successfully")
            
            # Show status
            logger.info("📊 Service Status:")
            self.run_command(f"systemctl status {self.service_name} --no-pager", check=False)
            self.run_command("systemctl status smart-locker-admin --no-pager", check=False)
            
        except Exception as e:
            logger.error(f"❌ Failed to start services: {e}")
    
    def stop_services(self):
        """Stop all services"""
        logger.info("🛑 Stopping services...")
        
        try:
            self.run_command(f"sudo systemctl stop {self.service_name}")
            self.run_command("sudo systemctl stop smart-locker-admin")
            
            logger.info("✅ Services stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop services: {e}")
    
    def uninstall(self):
        """Uninstall the system"""
        logger.info("🗑️ Uninstalling Smart Locker system...")
        
        response = input("Are you sure you want to uninstall? This will remove all data! (y/N): ")
        if response.lower() != 'y':
            logger.info("Uninstall cancelled")
            return
        
        try:
            # Stop and disable services
            self.run_command(f"sudo systemctl stop {self.service_name}", check=False)
            self.run_command("sudo systemctl stop smart-locker-admin", check=False)
            self.run_command(f"sudo systemctl disable {self.service_name}", check=False)
            self.run_command("sudo systemctl disable smart-locker-admin", check=False)
            
            # Remove service files
            self.run_command(f"sudo rm -f /etc/systemd/system/{self.service_name}.service")
            self.run_command("sudo rm -f /etc/systemd/system/smart-locker-admin.service")
            self.run_command("sudo systemctl daemon-reload")
            
            # Remove installation directory
            self.run_command(f"sudo rm -rf {self.target_dir}")
            
            # Remove cron job
            self.run_command('crontab -l | grep -v "backup_system.sh" | crontab -', check=False)
            
            logger.info("✅ Uninstall completed")
            
        except Exception as e:
            logger.error(f"❌ Uninstall failed: {e}")

def main():
    """Main deployment script"""
    parser = argparse.ArgumentParser(description="Smart Locker Raspberry Pi Deployment")
    parser.add_argument("action", choices=["deploy", "start", "stop", "status", "uninstall"], 
                       help="Action to perform")
    parser.add_argument("--source", default=".", help="Source directory (default: current)")
    parser.add_argument("--target", default="/opt/smart_locker", help="Target directory")
    parser.add_argument("--ssl", action="store_true", help="Enable SSL certificate generation")
    
    args = parser.parse_args()
    
    # Initialize deployer
    deployer = RaspberryPiDeployer(args.target)
    
    if args.action == "deploy":
        success = deployer.deploy(args.source, args.ssl)
        sys.exit(0 if success else 1)
    
    elif args.action == "start":
        deployer.start_services()
    
    elif args.action == "stop":
        deployer.stop_services()
    
    elif args.action == "status":
        deployer.run_command(f"systemctl status {deployer.service_name} --no-pager", check=False)
        deployer.run_command("systemctl status smart-locker-admin --no-pager", check=False)
    
    elif args.action == "uninstall":
        deployer.uninstall()

if __name__ == "__main__":
    main()