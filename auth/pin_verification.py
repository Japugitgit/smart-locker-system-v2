import bcrypt
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
from pathlib import Path

class PINVerification:
    """
    Core PIN verification and user security management system.
    Handles PIN hashing, verification, lockout policies, and security tracking.
    """
    
    def __init__(self, users_file="data/users.json", logs_file="data/access_logs.json"):
        self.users_file = users_file
        self.logs_file = logs_file
        self.load_data()
        
    def load_data(self):
        """Load users database and access logs from JSON files"""
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except FileNotFoundError:
            self.users = {}
            
        try:
            with open(self.logs_file, 'r') as f:
                self.access_logs = json.load(f)
        except FileNotFoundError:
            self.access_logs = {"logs": [], "summary": {}}
    
    def save_users(self):
        """Save users database to JSON file"""
        # Ensure directory exists
        Path(self.users_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def save_logs(self):
        """Save access logs to JSON file"""
        # Ensure directory exists
        Path(self.logs_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.logs_file, 'w') as f:
            json.dump(self.access_logs, f, indent=2)
    
    def hash_pin(self, pin: str) -> str:
        """Hash PIN with bcrypt for secure storage"""
        return bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_pin(self, user_id: str, pin: str) -> Tuple[bool, str]:
        """
        Verify PIN for specified user with security checks
        
        Args:
            user_id: User identifier
            pin: 4-digit PIN to verify
            
        Returns:
            Tuple of (success_boolean, reason_string)
        """
        if user_id not in self.users:
            return False, "user_not_found"
        
        user = self.users[user_id]
        
        # Security checks
        if self.is_user_locked_out(user_id):
            return False, "user_locked_out"
        
        if not user.get('active', True):
            return False, "account_disabled"
        
        # PIN verification
        stored_hash = user.get('pin_hash')
        if not stored_hash:
            return False, "pin_not_set"
        
        if bcrypt.checkpw(pin.encode('utf-8'), stored_hash.encode('utf-8')):
            # Success - reset failed attempts and update access time
            self.users[user_id]['pin_failed_attempts'] = 0
            self.users[user_id]['last_access'] = datetime.now().isoformat()
            self.save_users()
            return True, "success"
        else:
            # Failed - increment attempts and apply lockout if needed
            self.increment_pin_failures(user_id)
            return False, "wrong_pin"
    
    def set_pin(self, user_id: str, pin: str) -> bool:
        """
        Set or update PIN for user with validation
        
        Args:
            user_id: User identifier
            pin: 4-digit PIN string
            
        Returns:
            Success boolean
        """
        if len(pin) != 4 or not pin.isdigit():
            return False
        
        if user_id not in self.users:
            return False
        
        # Store both plaintext (for display) and hash (for security)
        self.users[user_id]['pin'] = pin  
        self.users[user_id]['pin_hash'] = self.hash_pin(pin)
        self.save_users()
        return True
    
    def increment_pin_failures(self, user_id: str):
        """Increment PIN failure count and apply lockout policy"""
        user = self.users[user_id]
        user['pin_failed_attempts'] = user.get('pin_failed_attempts', 0) + 1
        user['last_failed'] = datetime.now().isoformat()
        
        max_attempts = user.get('max_pin_attempts', 3)
        if user['pin_failed_attempts'] >= max_attempts:
            lockout_duration = user.get('lockout_duration', 300)  # 5 minutes default
            lockout_until = datetime.now() + timedelta(seconds=lockout_duration)
            user['lockout_until'] = lockout_until.isoformat()
        
        self.save_users()
    
    def is_user_locked_out(self, user_id: str) -> bool:
        """Check if user is currently locked out due to failed attempts"""
        user = self.users.get(user_id, {})
        lockout_until = user.get('lockout_until')
        
        if not lockout_until:
            return False
        
        lockout_time = datetime.fromisoformat(lockout_until)
        if datetime.now() > lockout_time:
            # Lockout expired - clear lockout status
            self.users[user_id]['lockout_until'] = None
            self.users[user_id]['pin_failed_attempts'] = 0
            self.save_users()
            return False
        
        return True
    
    def get_user_security_status(self, user_id: str) -> Dict:
        """Get comprehensive security status for user"""
        if user_id not in self.users:
            return {"status": "user_not_found"}
        
        user = self.users[user_id]
        return {
            "user_id": user_id,
            "active": user.get('active', True),
            "pin_set": bool(user.get('pin_hash')),
            "failed_attempts": user.get('pin_failed_attempts', 0),
            "locked_out": self.is_user_locked_out(user_id),
            "lockout_until": user.get('lockout_until'),
            "last_access": user.get('last_access'),
            "last_failed": user.get('last_failed'),
            "access_level": user.get('access_level', 'user')
        }
    
    def unlock_user(self, user_id: str, admin_override: bool = False) -> bool:
        """Manually unlock user (admin function)"""
        if user_id not in self.users:
            return False
        
        self.users[user_id]['pin_failed_attempts'] = 0
        self.users[user_id]['lockout_until'] = None
        if admin_override:
            self.users[user_id]['last_access'] = datetime.now().isoformat()
        self.save_users()
        return True
    
    def get_all_users_status(self) -> List[Dict]:
        """Get security status for all users"""
        return [self.get_user_security_status(user_id) for user_id in self.users.keys()]
    
    def create_user_with_pin(self, user_id: str, name: str, pin: str, access_level: str = "user") -> bool:
        """Create new user with PIN (used for testing/admin)"""
        if user_id in self.users:
            return False  # User already exists
        
        if len(pin) != 4 or not pin.isdigit():
            return False  # Invalid PIN format
        
        # Create new user with minimal data
        self.users[user_id] = {
            "name": name,
            "registration_date": datetime.now().isoformat(),
            "audio_files": [],
            "embedding": [],
            "sample_count": 0,
            # PIN authentication fields
            "pin": pin,
            "pin_hash": self.hash_pin(pin),
            "access_level": access_level,
            "active": True,
            # Security tracking
            "failed_attempts": 0,
            "pin_failed_attempts": 0,
            "last_access": None,
            "last_failed": None,
            "lockout_until": None,
            # Security policies
            "max_voice_attempts": 3,
            "max_pin_attempts": 3,
            "lockout_duration": 300
        }
        
        self.save_users()
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user from system"""
        if user_id not in self.users:
            return False
        
        del self.users[user_id]
        self.save_users()
        return True
    
    def update_user_access_level(self, user_id: str, access_level: str) -> bool:
        """Update user access level"""
        if user_id not in self.users:
            return False
        
        valid_levels = ["user", "admin", "guest", "disabled"]
        if access_level not in valid_levels:
            return False
        
        self.users[user_id]['access_level'] = access_level
        self.users[user_id]['active'] = access_level != "disabled"
        self.save_users()
        return True
    
    def get_user_count(self) -> Dict[str, int]:
        """Get user statistics"""
        total = len(self.users)
        active = sum(1 for user in self.users.values() if user.get('active', True))
        locked = sum(1 for user_id in self.users.keys() if self.is_user_locked_out(user_id))
        
        return {
            "total": total,
            "active": active,
            "locked": locked,
            "inactive": total - active
        }