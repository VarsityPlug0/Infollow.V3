from app import app, db
from models import Job, DonatedAccount, Target, ActionLog, User

with app.app_context():
    print("🔍 Checking current database state...")
    
    # Count existing records
    jobs_count = Job.query.count()
    accounts_count = DonatedAccount.query.count()
    targets_count = Target.query.count()
    actions_count = ActionLog.query.count()
    users_count = User.query.count()
    
    print(f"Current database contents:")
    print(f"  - Jobs: {jobs_count}")
    print(f"  - Donor Accounts: {accounts_count}")
    print(f"  - Targets: {targets_count}")
    print(f"  - Action Logs: {actions_count}")
    print(f"  - Users: {users_count}")
    
    # Delete all records
    print("\n🗑️  Deleting all records...")
    ActionLog.query.delete()
    Job.query.delete()
    Target.query.delete()
    DonatedAccount.query.delete()
    User.query.delete()
    
    # Commit changes
    db.session.commit()
    print("✅ All records deleted successfully!")
    
    # Verify reset
    new_jobs_count = Job.query.count()
    new_accounts_count = DonatedAccount.query.count()
    new_targets_count = Target.query.count()
    new_actions_count = ActionLog.query.count()
    new_users_count = User.query.count()
    
    print(f"\n📊 Database after reset:")
    print(f"  - Jobs: {new_jobs_count}")
    print(f"  - Donor Accounts: {new_accounts_count}")
    print(f"  - Targets: {new_targets_count}")
    print(f"  - Action Logs: {new_actions_count}")
    print(f"  - Users: {new_users_count}")
    
    print("\n✅ Database reset completed successfully!")