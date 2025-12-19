from app import app, db
import os

print("🔍 Testing database configuration...")
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Check if we're using the right database URI
if 'barter.db' in app.config['SQLALCHEMY_DATABASE_URI']:
    print("✅ Using barter.db as database")
else:
    print("⚠️  Not using barter.db - this might be the issue")

# Try to create all tables
try:
    with app.app_context():
        print("🔄 Attempting to create all tables...")
        db.create_all()
        print("✅ Tables created successfully!")
except Exception as e:
    print(f"❌ Error creating tables: {e}")

# Check if database file exists now
import os
if os.path.exists('barter.db'):
    print("✅ barter.db file exists")
else:
    print("❌ barter.db file does not exist")