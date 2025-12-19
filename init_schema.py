from app import app, db

with app.app_context():
    print("Creating database schema...")
    db.create_all()
    print("✅ Database schema created successfully!")