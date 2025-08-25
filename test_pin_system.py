#!/usr/bin/env python3
"""
Test script for PIN verification system
Tests core authentication functionality
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from auth.pin_verification import PINVerification
from auth.access_control import AccessControl
from auth.migration import DatabaseMigration

def test_pin_verification():
    """Test PIN verification functionality"""
    print("🔐 Testing PIN Verification System...")
    
    # Initialize PIN verifier
    pin_verifier = PINVerification("test_users.json", "test_logs.json")
    
    # Create test user
    success = pin_verifier.create_user_with_pin("test_user", "Test User", "1234")
    print(f"Create test user: {'✅' if success else '❌'}")
    
    # Test PIN verification - correct PIN
    success, reason = pin_verifier.verify_pin("test_user", "1234")
    print(f"Verify correct PIN: {'✅' if success else '❌'} ({reason})")
    
    # Test PIN verification - wrong PIN
    success, reason = pin_verifier.verify_pin("test_user", "0000")
    print(f"Verify wrong PIN: {'❌' if not success else '⚠️'} ({reason})")
    
    # Test PIN change
    success = pin_verifier.set_pin("test_user", "5678")
    print(f"Change PIN: {'✅' if success else '❌'}")
    
    # Verify new PIN
    success, reason = pin_verifier.verify_pin("test_user", "5678")
    print(f"Verify new PIN: {'✅' if success else '❌'} ({reason})")
    
    # Test lockout mechanism
    print("\n🔒 Testing lockout mechanism...")
    for i in range(4):  # Should trigger lockout after 3 attempts
        success, reason = pin_verifier.verify_pin("test_user", "0000")
        print(f"Failed attempt {i+1}: {reason}")
        
        if reason == "user_locked_out":
            print("✅ Lockout mechanism working correctly")
            break
    
    # Test user security status
    status = pin_verifier.get_user_security_status("test_user")
    print(f"\nUser status: {status}")
    
    # Cleanup test files
    import os
    try:
        os.remove("test_users.json")
        os.remove("test_logs.json")
        print("🧹 Cleaned up test files")
    except FileNotFoundError:
        pass
    
    print("✅ PIN verification tests completed\n")

def test_access_control():
    """Test access control functionality"""
    print("🚪 Testing Access Control System...")
    
    # Initialize access control
    access_control = AccessControl()
    
    # Create test user first
    access_control.pin_verifier.create_user_with_pin("test_user", "Test User", "1234")
    
    # Test voice + PIN authentication
    result = access_control.authenticate_user(
        user_id="test_user",
        voice_confidence=0.85,
        gmm_score=0.72,
        pin="1234",
        method="voice_pin"
    )
    
    print(f"Voice + PIN auth: {'✅' if result['success'] else '❌'} ({result['reason']})")
    print(f"Session duration: {result['session_duration_ms']}ms")
    
    # Test low voice confidence
    result = access_control.authenticate_user(
        user_id="test_user",
        voice_confidence=0.5,  # Below threshold
        gmm_score=0.72,
        pin="1234",
        method="voice_pin"
    )
    
    print(f"Low voice confidence: {'❌' if not result['success'] else '⚠️'} ({result['reason']})")
    
    # Test PIN-only authentication
    result = access_control.pin_only_authentication("test_user", "1234")
    print(f"PIN-only auth: {'✅' if result['success'] else '❌'} ({result['reason']})")
    
    # Test emergency unlock
    result = access_control.emergency_unlock("0000")  # Default admin PIN
    print(f"Emergency unlock: {'✅' if result['success'] else '❌'} ({result['reason']})")
    
    # Test admin authentication
    result = access_control.admin_authentication("0000")
    print(f"Admin auth: {'✅' if result['success'] else '❌'} ({result['reason']})")
    
    # Get access statistics
    stats = access_control.get_access_statistics(days=1)
    print(f"\nAccess statistics:")
    print(f"  Total attempts: {stats['total_attempts']}")
    print(f"  Success rate: {stats['success_rate']:.2%}")
    print(f"  Unique users: {stats['unique_users']}")
    
    # Get recent logs
    recent_logs = access_control.get_recent_access_logs(limit=5)
    print(f"\nRecent access logs: {len(recent_logs)} entries")
    
    # Cleanup
    try:
        os.remove("data/users.json")
        os.remove("data/access_logs.json")
        os.rmdir("data")
        print("🧹 Cleaned up test files")
    except (FileNotFoundError, OSError):
        pass
    
    print("✅ Access control tests completed\n")

def test_migration():
    """Test database migration"""
    print("🔄 Testing Database Migration...")
    
    # Create sample old format users.json
    old_users = {
        "user1": {
            "name": "User One",
            "registration_date": "2025-01-01T00:00:00",
            "audio_files": ["user1_sample1.wav"],
            "embedding": [1.0, 2.0, 3.0],
            "sample_count": 1
        },
        "user2": {
            "name": "User Two", 
            "registration_date": "2025-01-02T00:00:00",
            "audio_files": ["user2_sample1.wav"],
            "embedding": [4.0, 5.0, 6.0],
            "sample_count": 1
        }
    }
    
    # Create test file
    import json
    os.makedirs("test_data", exist_ok=True)
    with open("test_data/users.json", "w") as f:
        json.dump(old_users, f, indent=2)
    
    # Test migration
    migration = DatabaseMigration("test_data/users.json")
    
    # Check status before migration
    status = migration.get_migration_status()
    print(f"Before migration - Users: {status['user_count']}, Migrated: {status['migrated']}")
    
    # Run migration
    success = migration.migrate_to_pin_system()
    print(f"Migration: {'✅' if success else '❌'}")
    
    # Verify migration
    verified = migration.verify_migration()
    print(f"Verification: {'✅' if verified else '❌'}")
    
    # Check status after migration
    status = migration.get_migration_status()
    print(f"After migration - Users: {status['user_count']}, Migrated: {status['migrated']}")
    
    # Test adding admin user
    admin_added = migration.add_admin_user("9999")
    print(f"Add admin user: {'✅' if admin_added else '❌'}")
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree("test_data")
        print("🧹 Cleaned up test files")
    except FileNotFoundError:
        pass
    
    print("✅ Migration tests completed\n")

def test_performance():
    """Test system performance"""
    print("⚡ Testing Performance...")
    
    import time
    
    # Initialize systems
    pin_verifier = PINVerification("perf_users.json", "perf_logs.json")
    access_control = AccessControl()
    
    # Create test users
    num_users = 10
    print(f"Creating {num_users} test users...")
    
    start_time = time.time()
    for i in range(num_users):
        pin_verifier.create_user_with_pin(f"user_{i}", f"User {i}", f"{i:04d}")
    
    creation_time = time.time() - start_time
    print(f"User creation: {creation_time:.3f}s ({creation_time/num_users:.3f}s per user)")
    
    # Test PIN verification speed
    print("Testing PIN verification speed...")
    
    times = []
    for i in range(100):
        start_time = time.time()
        pin_verifier.verify_pin("user_0", "0000")
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    print(f"PIN verification: {avg_time*1000:.3f}ms average")
    
    # Test full authentication flow
    print("Testing full authentication flow...")
    
    times = []
    for i in range(50):
        start_time = time.time()
        access_control.authenticate_user(
            user_id="user_0",
            voice_confidence=0.85,
            gmm_score=0.75,
            pin="0000"
        )
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    print(f"Full authentication: {avg_time*1000:.3f}ms average")
    
    # Cleanup
    try:
        os.remove("perf_users.json")
        os.remove("perf_logs.json")
        print("🧹 Cleaned up performance test files")
    except FileNotFoundError:
        pass
    
    print("✅ Performance tests completed\n")

def main():
    """Main test function"""
    print("🧪 Smart Locker PIN System Test Suite")
    print("=" * 50)
    print(f"Test started: {datetime.now().isoformat()}")
    print()
    
    try:
        # Run all tests
        test_pin_verification()
        test_access_control()
        test_migration()
        test_performance()
        
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)