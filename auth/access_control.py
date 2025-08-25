import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from .pin_verification import PINVerification

class AccessControl:
    """
    Main authentication flow controller that orchestrates voice recognition
    and PIN verification for complete 2-factor authentication.
    """
    
    def __init__(self):
        self.pin_verifier = PINVerification()
        
    def authenticate_user(self, user_id: str, voice_confidence: float, 
                         gmm_score: float, pin: str, method: str = "voice_pin") -> Dict:
        """
        Complete 2-factor authentication: voice recognition + PIN verification
        
        Args:
            user_id: Identified user from voice recognition
            voice_confidence: ECAPA-TDNN confidence score (0.0-1.0)
            gmm_score: GMM model confidence score
            pin: 4-digit PIN entered by user
            method: Authentication method used
            
        Returns:
            Dictionary with authentication result and details
        """
        auth_result = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "voice_confidence": voice_confidence,
            "gmm_score": gmm_score,
            "pin_attempts": 1,
            "method": method,
            "success": False,
            "reason": None,
            "door_opened": False,
            "session_duration_ms": 0
        }
        
        start_time = datetime.now()
        
        # Voice recognition threshold check (configurable)
        voice_threshold = 0.7  # Can be moved to config
        if method == "voice_pin" and voice_confidence < voice_threshold:
            auth_result["success"] = False
            auth_result["reason"] = "voice_confidence_low"
            auth_result["session_duration_ms"] = self._get_duration_ms(start_time)
            self.log_access_attempt(auth_result)
            return auth_result
        
        # PIN verification
        pin_valid, pin_reason = self.pin_verifier.verify_pin(user_id, pin)
        
        if pin_valid:
            auth_result["success"] = True
            auth_result["reason"] = "authenticated"
            auth_result["door_opened"] = True  # Will be set by hardware controller
        else:
            auth_result["success"] = False
            auth_result["reason"] = pin_reason
        
        auth_result["session_duration_ms"] = self._get_duration_ms(start_time)
        self.log_access_attempt(auth_result)
        return auth_result
    
    def pin_only_authentication(self, user_id: str, pin: str) -> Dict:
        """
        PIN-only authentication (fallback when voice recognition fails repeatedly)
        """
        return self.authenticate_user(
            user_id=user_id,
            voice_confidence=0.0,
            gmm_score=0.0,
            pin=pin,
            method="pin_only"
        )
    
    def emergency_unlock(self, admin_pin: str, user_id: str = "admin") -> Dict:
        """
        Emergency access with admin PIN - bypasses normal security checks
        
        Args:
            admin_pin: Master admin PIN
            user_id: Admin user identifier
            
        Returns:
            Authentication result dictionary
        """
        auth_result = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "voice_confidence": None,
            "gmm_score": None,
            "pin_attempts": 1,
            "method": "emergency",
            "success": False,
            "reason": None,
            "door_opened": False
        }
        
        # Check admin PIN (should be configurable in production)
        ADMIN_PIN = "0000"  # TODO: Move to secure configuration
        
        if admin_pin == ADMIN_PIN:
            auth_result["success"] = True
            auth_result["reason"] = "emergency_access_granted"
            auth_result["door_opened"] = True
        else:
            auth_result["success"] = False
            auth_result["reason"] = "invalid_admin_pin"
        
        self.log_access_attempt(auth_result)
        return auth_result
    
    def admin_authentication(self, admin_pin: str) -> Dict:
        """
        Admin authentication for system management
        
        Args:
            admin_pin: Admin PIN
            
        Returns:
            Authentication result dictionary
        """
        auth_result = {
            "id": str(uuid.uuid4()),
            "user_id": "admin",
            "timestamp": datetime.now().isoformat(),
            "voice_confidence": None,
            "gmm_score": None,
            "pin_attempts": 1,
            "method": "admin",
            "success": False,
            "reason": None,
            "door_opened": False
        }
        
        # Check admin PIN
        ADMIN_PIN = "0000"  # TODO: Move to secure configuration
        
        if admin_pin == ADMIN_PIN:
            auth_result["success"] = True
            auth_result["reason"] = "admin_access_granted"
        else:
            auth_result["success"] = False
            auth_result["reason"] = "invalid_admin_pin"
        
        self.log_access_attempt(auth_result)
        return auth_result
    
    def get_access_statistics(self, days: int = 7) -> Dict:
        """Get access statistics for specified number of days"""
        logs = self.pin_verifier.access_logs.get("logs", [])
        
        # Filter logs by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_logs = [
            log for log in logs 
            if datetime.fromisoformat(log["timestamp"]) > cutoff_date
        ]
        
        if not recent_logs:
            return {
                "period_days": days,
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "success_rate": 0.0,
                "unique_users": 0,
                "methods": {},
                "failure_reasons": {}
            }
        
        successful = len([log for log in recent_logs if log["success"]])
        failed = len([log for log in recent_logs if not log["success"]])
        
        # Count methods
        methods = {}
        for log in recent_logs:
            method = log.get("method", "unknown")
            methods[method] = methods.get(method, 0) + 1
        
        # Count failure reasons
        failure_reasons = {}
        for log in recent_logs:
            if not log["success"]:
                reason = log.get("reason", "unknown")
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        return {
            "period_days": days,
            "total_attempts": len(recent_logs),
            "successful_attempts": successful,
            "failed_attempts": failed,
            "success_rate": successful / len(recent_logs),
            "unique_users": len(set(log["user_id"] for log in recent_logs)),
            "methods": methods,
            "failure_reasons": failure_reasons
        }
    
    def get_recent_access_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent access logs"""
        logs = self.pin_verifier.access_logs.get("logs", [])
        
        # Sort by timestamp (most recent first)
        sorted_logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
        
        return sorted_logs[:limit]
    
    def get_user_access_history(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get access history for specific user"""
        logs = self.pin_verifier.access_logs.get("logs", [])
        
        # Filter by user and date range
        cutoff_date = datetime.now() - timedelta(days=days)
        user_logs = [
            log for log in logs 
            if log["user_id"] == user_id and 
            datetime.fromisoformat(log["timestamp"]) > cutoff_date
        ]
        
        # Sort by timestamp (most recent first)
        return sorted(user_logs, key=lambda x: x["timestamp"], reverse=True)
    
    def log_access_attempt(self, auth_result: Dict):
        """Log access attempt to persistent storage"""
        self.pin_verifier.access_logs["logs"].append(auth_result)
        
        # Update summary statistics
        summary = self.pin_verifier.access_logs.get("summary", {})
        today = datetime.now().date().isoformat()
        
        if summary.get("date") != today:
            # New day - reset counters
            summary = {
                "date": today,
                "total_attempts_today": 0,
                "successful_today": 0,
                "failed_today": 0
            }
        
        summary["total_attempts_today"] += 1
        if auth_result["success"]:
            summary["successful_today"] += 1
        else:
            summary["failed_today"] += 1
        
        summary["last_updated"] = datetime.now().isoformat()
        self.pin_verifier.access_logs["summary"] = summary
        
        self.pin_verifier.save_logs()
    
    def cleanup_old_logs(self, days_to_keep: int = 90):
        """Remove access logs older than specified days"""
        logs = self.pin_verifier.access_logs.get("logs", [])
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Keep only recent logs
        recent_logs = [
            log for log in logs 
            if datetime.fromisoformat(log["timestamp"]) > cutoff_date
        ]
        
        # Update logs
        self.pin_verifier.access_logs["logs"] = recent_logs
        self.pin_verifier.save_logs()
        
        return len(logs) - len(recent_logs)  # Return number of removed logs
    
    def get_security_alerts(self) -> List[Dict]:
        """Get security alerts based on recent activity"""
        alerts = []
        
        # Check for users with recent lockouts
        for user_id in self.pin_verifier.users.keys():
            if self.pin_verifier.is_user_locked_out(user_id):
                user = self.pin_verifier.users[user_id]
                alerts.append({
                    "type": "user_lockout",
                    "severity": "medium",
                    "user_id": user_id,
                    "message": f"User {user_id} is currently locked out",
                    "timestamp": user.get("last_failed"),
                    "lockout_until": user.get("lockout_until")
                })
        
        # Check for repeated failures
        recent_logs = self.get_recent_access_logs(100)
        failure_counts = {}
        
        for log in recent_logs:
            if not log["success"]:
                user_id = log["user_id"]
                failure_counts[user_id] = failure_counts.get(user_id, 0) + 1
        
        for user_id, count in failure_counts.items():
            if count >= 5:  # 5 or more failures
                alerts.append({
                    "type": "repeated_failures",
                    "severity": "high",
                    "user_id": user_id,
                    "message": f"User {user_id} has {count} recent failures",
                    "failure_count": count
                })
        
        return alerts
    
    def verify_admin_pin(self, pin: str) -> Dict:
        """
        Verify admin PIN - wrapper around admin_authentication for compatibility
        
        Args:
            pin: Admin PIN to verify
            
        Returns:
            Authentication result dictionary with success field
        """
        return self.admin_authentication(pin)
    
    def authenticate_pin_only(self, pin: str) -> Dict:
        """
        PIN-only authentication - find user by PIN and authenticate
        
        Args:
            pin: 4-digit PIN to authenticate
            
        Returns:
            Authentication result dictionary
        """
        # Find user by PIN
        for user_id in self.pin_verifier.users.keys():
            pin_valid, _ = self.pin_verifier.verify_pin(user_id, pin)
            if pin_valid:
                # Found matching user, authenticate with PIN only
                return self.pin_only_authentication(user_id, pin)
        
        # No user found with this PIN
        auth_result = {
            "id": str(uuid.uuid4()),
            "user_id": "unknown",
            "timestamp": datetime.now().isoformat(),
            "voice_confidence": 0.0,
            "gmm_score": 0.0,
            "pin_attempts": 1,
            "method": "pin_only",
            "success": False,
            "reason": "pin_not_found",
            "door_opened": False,
            "session_duration_ms": 0
        }
        
        self.log_access_attempt(auth_result)
        return auth_result

    def _get_duration_ms(self, start_time: datetime) -> int:
        """Calculate duration in milliseconds from start time"""
        return int((datetime.now() - start_time).total_seconds() * 1000)