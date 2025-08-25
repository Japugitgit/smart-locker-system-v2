import json
import shutil
import bcrypt
from datetime import datetime
from pathlib import Path

class DatabaseMigration:
    """
    Handles migration of existing users.json to include PIN verification fields
    and creates necessary data structures for the new authentication system.
    """
    
    def __init__(self, users_file="data/users.json", backup_suffix="_backup"):
        self.users_file = users_file
        self.backup_suffix = backup_suffix
        
    def migrate_to_pin_system(self) -> bool:
        """
        Migrate existing users database to include PIN verification fields
        
        Returns:
            Success boolean
        """
        try:
            # Check if file exists
            if not Path(self.users_file).exists():
                print(f"⚠️  Users file not found: {self.users_file}")
                print("Creating new empty users database...")
                self._create_empty_users_file()
                return True
            
            # Create backup of original file
            backup_path = f"{self.users_file}{self.backup_suffix}.json"
            shutil.copy(self.users_file, backup_path)
            print(f"✅ Backup created: {backup_path}")
            
            # Load existing users
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            if not users:
                print("📝 Users file is empty, no migration needed")
                return True
            
            # Check if already migrated
            first_user = next(iter(users.values()))
            if 'pin_hash' in first_user:
                print("✅ Users database already migrated")
                return True
            
            # Migrate each user
            migrated_count = 0
            for user_id, user_data in users.items():
                print(f"Migrating user: {user_id}")
                
                # Generate default PIN (last 4 digits of user_id hash)
                default_pin = str(abs(hash(user_id)))[-4:].zfill(4)
                
                # Add new authentication fields
                user_data.update({
                    # PIN authentication
                    "pin": default_pin,
                    "pin_hash": bcrypt.hashpw(default_pin.encode(), bcrypt.gensalt()).decode(),
                    
                    # Access control
                    "access_level": "user",
                    "active": True,
                    
                    # Security tracking
                    "failed_attempts": 0,
                    "pin_failed_attempts": 0,
                    "last_access": user_data.get("registration_date"),
                    "last_failed": None,
                    "lockout_until": None,
                    
                    # Security policies (configurable per user)
                    "max_voice_attempts": 3,
                    "max_pin_attempts": 3,
                    "lockout_duration": 300  # 5 minutes
                })
                
                migrated_count += 1
            
            # Save migrated data
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            print(f"✅ {migrated_count} users migrated successfully")
            
            # Create access logs file
            self._create_access_logs_file()
            
            # Print migration summary
            self._print_migration_summary(users)
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            # Restore backup if migration fails
            backup_path = f"{self.users_file}{self.backup_suffix}.json"
            if Path(backup_path).exists():
                shutil.copy(backup_path, self.users_file)
                print(f"🔄 Restored from backup")
            return False
    
    def _create_empty_users_file(self):
        """Create empty users.json file with proper structure"""
        # Ensure directory exists
        Path(self.users_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.users_file, 'w') as f:
            json.dump({}, f, indent=2)
        
        print(f"✅ Created empty users file: {self.users_file}")
    
    def _create_access_logs_file(self):
        """Create initial access logs file structure"""
        logs_file = "data/access_logs.json"
        
        # Ensure directory exists
        Path(logs_file).parent.mkdir(parents=True, exist_ok=True)
        
        initial_logs = {
            "logs": [],
            "summary": {
                "date": datetime.now().date().isoformat(),
                "total_attempts_today": 0,
                "successful_today": 0,
                "failed_today": 0,
                "last_updated": datetime.now().isoformat()
            },
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Access logs for Smart Locker System"
            }
        }
        
        with open(logs_file, 'w') as f:
            json.dump(initial_logs, f, indent=2)
        
        print(f"✅ Access logs file created: {logs_file}")
    
    def _print_migration_summary(self, users: dict):
        """Print summary of migration results"""
        print("\n📊 MIGRATION SUMMARY")
        print("=" * 50)
        print(f"Total users migrated: {len(users)}")
        print(f"Default PINs assigned: {len(users)}")
        print("\nUser PIN assignments:")
        for user_id, user_data in users.items():
            access_level = user_data.get('access_level', 'user')
            print(f"  {user_id}: PIN {user_data['pin']} (level: {access_level})")
        
        print("\n⚠️  IMPORTANT SECURITY NOTES:")
        print("1. Default PINs have been assigned to all users")
        print("2. Users should change their PINs immediately")
        print("3. Default PINs are based on user_id hash (predictable)")
        print("4. Use the admin interface to set secure PINs")
        print("5. Backup file contains original data without PINs")
        print("\n🔐 NEXT STEPS:")
        print("1. Update admin PIN in security configuration")
        print("2. Set secure PINs for all users")
        print("3. Test authentication flow")
        print("4. Review security policies")
    
    def rollback_migration(self) -> bool:
        """
        Rollback migration by restoring from backup
        
        Returns:
            Success boolean
        """
        backup_path = f"{self.users_file}{self.backup_suffix}.json"
        
        if not Path(backup_path).exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False
        
        try:
            shutil.copy(backup_path, self.users_file)
            print(f"✅ Migration rolled back successfully")
            print(f"📁 Restored from: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            return False
    
    def verify_migration(self) -> bool:
        """
        Verify that migration was successful by checking required fields
        
        Returns:
            Verification success boolean
        """
        required_fields = [
            'pin', 'pin_hash', 'access_level', 'active',
            'failed_attempts', 'pin_failed_attempts', 'last_access'
        ]
        
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            if not users:
                print("✅ Empty users database - migration verification passed")
                return True
            
            for user_id, user_data in users.items():
                for field in required_fields:
                    if field not in user_data:
                        print(f"❌ Missing field '{field}' in user {user_id}")
                        return False
                
                # Verify PIN hash is valid bcrypt hash
                pin_hash = user_data.get('pin_hash', '')
                if not pin_hash.startswith('$2b$'):
                    print(f"❌ Invalid PIN hash format for user {user_id}")
                    return False
                
                # Verify PIN is 4 digits
                pin = user_data.get('pin', '')
                if not (len(pin) == 4 and pin.isdigit()):
                    print(f"❌ Invalid PIN format for user {user_id}")
                    return False
            
            print(f"✅ Migration verification passed for {len(users)} users")
            return True
            
        except Exception as e:
            print(f"❌ Migration verification failed: {str(e)}")
            return False
    
    def add_admin_user(self, admin_pin: str = "0000") -> bool:
        """Add admin user to the system"""
        try:
            # Load users
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            # Add admin user
            admin_user_id = "admin"
            if admin_user_id in users:
                print(f"⚠️  Admin user already exists")
                return False
            
            users[admin_user_id] = {
                "name": "System Administrator",
                "registration_date": datetime.now().isoformat(),
                "audio_files": [],
                "embedding": [],
                "sample_count": 0,
                # PIN authentication
                "pin": admin_pin,
                "pin_hash": bcrypt.hashpw(admin_pin.encode(), bcrypt.gensalt()).decode(),
                "access_level": "admin",
                "active": True,
                # Security tracking
                "failed_attempts": 0,
                "pin_failed_attempts": 0,
                "last_access": None,
                "last_failed": None,
                "lockout_until": None,
                # Security policies
                "max_voice_attempts": 5,
                "max_pin_attempts": 5,
                "lockout_duration": 600  # 10 minutes
            }
            
            # Save updated users
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            print(f"✅ Admin user added with PIN: {admin_pin}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add admin user: {str(e)}")
            return False
    
    def get_migration_status(self) -> dict:
        """Get current migration status"""
        status = {
            "users_file_exists": Path(self.users_file).exists(),
            "backup_exists": Path(f"{self.users_file}{self.backup_suffix}.json").exists(),
            "logs_file_exists": Path("data/access_logs.json").exists(),
            "migrated": False,
            "user_count": 0,
            "errors": []
        }
        
        try:
            if status["users_file_exists"]:
                with open(self.users_file, 'r') as f:
                    users = json.load(f)
                
                status["user_count"] = len(users)
                
                # Check if migrated by looking for PIN fields
                if users:
                    first_user = next(iter(users.values()))
                    status["migrated"] = 'pin_hash' in first_user
                else:
                    status["migrated"] = True  # Empty file is considered migrated
                
        except Exception as e:
            status["errors"].append(str(e))
        
        return status

# CLI utility for running migration
def main():
    """CLI interface for database migration"""
    migration = DatabaseMigration()
    
    print("🔄 Smart Locker Database Migration Tool")
    print("=" * 50)
    
    # Check current status
    status = migration.get_migration_status()
    print(f"Users file exists: {status['users_file_exists']}")
    print(f"User count: {status['user_count']}")
    print(f"Already migrated: {status['migrated']}")
    
    if status['errors']:
        print(f"Errors: {', '.join(status['errors'])}")
        return
    
    if status['migrated']:
        print("✅ Database already migrated")
        
        # Verify migration
        if migration.verify_migration():
            print("✅ Migration verification passed")
        else:
            print("❌ Migration verification failed")
        return
    
    # Run migration
    print("\n🚀 Starting migration...")
    success = migration.migrate_to_pin_system()
    
    if success:
        print("\n🔍 Verifying migration...")
        if migration.verify_migration():
            print("\n🎉 Migration completed successfully!")
            
            # Ask about adding admin user
            try:
                response = input("\nAdd admin user? (y/N): ").lower().strip()
                if response == 'y':
                    admin_pin = input("Enter admin PIN (default: 0000): ").strip()
                    if not admin_pin:
                        admin_pin = "0000"
                    migration.add_admin_user(admin_pin)
            except KeyboardInterrupt:
                print("\nSkipped admin user creation")
        else:
            print("\n⚠️  Migration completed but verification failed")
    else:
        print("\n💥 Migration failed!")

if __name__ == "__main__":
    main()