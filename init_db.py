from app import app, db

with app.app_context():
    print("🔄 Initializing database...")
    db.create_all()
    print("✅ Database initialized successfully!")
    print("📁 Database file created:", app.config['SQLALCHEMY_DATABASE_URI'])