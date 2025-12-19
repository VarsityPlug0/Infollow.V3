from app import app

print("=== APP CONFIGURATION ===")
print(f"SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Check if DATABASE_URL environment variable exists
import os
database_url = os.environ.get('DATABASE_URL')
if database_url:
    print(f"DATABASE_URL env var: {database_url}")
else:
    print("DATABASE_URL env var: Not set")

# Check current working directory
import os
print(f"Current working directory: {os.getcwd()}")

# Check if database file exists
db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
print(f"Expected database path: {db_path}")
print(f"Database file exists: {os.path.exists(db_path)}")