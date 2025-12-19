import os
import sys

print("=== DEBUG DATABASE CONFIGURATION ===")

# Check environment variables
print("Environment variables:")
print(f"  DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')}")

# Import app and check config
try:
    from app import app, db
    print("\nApp configuration:")
    print(f"  SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Test database creation
    print("\nTesting database creation...")
    with app.app_context():
        print("  Creating tables...")
        db.create_all()
        print("  ✅ Database tables created")
        
        # Try to add a test record
        from models import User
        print("  Testing database write...")
        test_user = User(session_id="test-reset-session")
        db.session.add(test_user)
        db.session.commit()
        print("  ✅ Test record written to database")
        
        # Clean up
        db.session.delete(test_user)
        db.session.commit()
        print("  ✅ Test record cleaned up")
        
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\nChecking for database files...")
import glob
db_files = glob.glob("*.db")
print(f"  Database files found: {db_files}")

if os.path.exists("barter.db"):
    print("  ✅ barter.db exists")
    print(f"  File size: {os.path.getsize('barter.db')} bytes")
else:
    print("  ❌ barter.db does not exist")