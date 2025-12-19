# Monkey-patch gevent FIRST (before any other imports)
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from config import Config
from models import db, User, DonatedAccount, Target, ActionLog, Job
from instagram import InstagramAutomation
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Configure SocketIO for Render deployment with explicit WebSocket support
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='gevent', 
    logger=True, 
    engineio_logger=True,
    transports=['websocket', 'polling'],
    allow_upgrades=True,
    cookie=None
)

ig_automation = InstagramAutomation(session_folder=app.config['SESSION_FOLDER'])

# Initialize database
with app.app_context():
    db.create_all()

def get_or_create_user():
    """Get or create user based on session"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        session['demo_mode'] = True  # New users start in demo mode
    
    user = User.query.filter_by(session_id=session['user_id']).first()
    if not user:
        user = User(session_id=session['user_id'], is_authenticated=False)
        db.session.add(user)
        db.session.commit()
    
    return user

def is_demo_mode():
    """Check if user is in demo mode"""
    user = get_or_create_user()
    return not user.is_authenticated

@app.route('/')
def index():
    """Simplified landing page - single input field"""
    user = get_or_create_user()
    return render_template('index.html', is_authenticated=user.is_authenticated)

@app.route('/donate')
def donate_page():
    """User-facing donation page"""
    return render_template('donate.html')

@app.route('/login')
def login_page():
    """Client login page"""
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    """Client login endpoint"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email required'}), 400
    
    # Find user by email
    from models import User
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'success': False, 'error': 'Account not found. Please sign up first.'}), 404
    
    # Log in user
    session['user_id'] = user.session_id
    session['demo_mode'] = False
    user.is_authenticated = True
    db.session.commit()
    
    print(f"[AUTH] User logged in: {email}")
    
    return jsonify({
        'success': True,
        'message': 'Logged in successfully!',
        'email': email
    })

@app.route('/logout')
def logout():
    """Client logout"""
    user = get_or_create_user()
    
    if user.is_authenticated:
        user.is_authenticated = False
        db.session.commit()
        print(f"[AUTH] User logged out: {user.email}")
    
    # Clear session
    session.clear()
    
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """User dashboard showing donation history and credits"""
    user = get_or_create_user()
    
    # Get user's donated accounts
    from models import DonatedAccount, Target, ActionLog
    from sqlalchemy import func
    
    # Check authentication
    if not user.is_authenticated:
        return redirect(url_for('index'))
    
    # Get ONLY accounts donated by this specific user
    donated_accounts = DonatedAccount.query.filter_by(user_id=user.id).order_by(DonatedAccount.donated_at.desc()).all()
    
    # Calculate stats based on user's data only
    user_targets = Target.query.filter_by(user_id=user.id).all()
    user_target_usernames = [t.username for t in user_targets]
    
    # Count successful deliveries for this user's targets
    total_delivered = ActionLog.query.filter(
        ActionLog.target.in_(user_target_usernames),
        ActionLog.result == 'success'
    ).count() if user_target_usernames else 0
    
    stats = {
        'available_credits': user.free_targets * 30,  # 30 followers per donation
        'donated_accounts': len(donated_accounts),  # Only user's donations
        'total_delivered': total_delivered  # Only followers delivered to user's targets
    }
    
    # Build activity timeline
    activities = []
    
    # Add donation activities
    for account in donated_accounts[:5]:  # Last 5 donations
        activities.append({
            'icon': 'gift',
            'title': f'Donated @{account.username}',
            'description': f'Earned 30 followers credit',
            'time': account.donated_at.strftime('%b %d, %Y at %I:%M %p'),
            'badge': '+30',
            'badge_type': 'unused'
        })
    
    # Add target activities
    targets = Target.query.filter_by(user_id=user.id).order_by(Target.created_at.desc()).limit(5).all()
    for target in targets:
        count = 20 if target.tier == 'free_test' else 30
        activities.append({
            'icon': 'rocket-takeoff',
            'title': f'Boosted @{target.username}',
            'description': f'Delivered {count} followers',
            'time': target.created_at.strftime('%b %d, %Y at %I:%M %p'),
            'badge': target.tier.replace('_', ' ').title(),
            'badge_type': 'free' if target.tier == 'free_test' else 'used'
        })
    
    # Sort activities by time (using string comparison since times are formatted)
    # For better sorting, we should use datetime objects
    activities_with_dt = []
    for activity in activities:
        # Parse the time string back to datetime for sorting
        if 'Donated' in activity['title']:
            account = DonatedAccount.query.filter_by(username=activity['title'].split('@')[1]).first()
            if account:
                activities_with_dt.append((account.donated_at, activity))
        else:
            target_username = activity['title'].split('@')[1]
            target = Target.query.filter_by(username=target_username).first()
            if target:
                activities_with_dt.append((target.created_at, activity))
    
    # Sort by datetime and extract activities
    activities_with_dt.sort(key=lambda x: x[0], reverse=True)
    sorted_activities = [a[1] for a in activities_with_dt]
    
    return render_template('dashboard.html', 
                         user=user, 
                         stats=stats, 
                         donated_accounts=donated_accounts,
                         activities=sorted_activities[:10])  # Show last 10 activities

@app.route('/api/lookup-profile', methods=['POST'])
def lookup_profile():
    """Lookup Instagram profile - bypasses verification on production (Render)"""
    data = request.get_json()
    username = data.get('username', '').strip().replace('@', '')
    
    if not username:
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    print(f"\n[LOOKUP] Fetching profile for @{username}...")
    
    # Check if running on Render (production) - skip Instagram API due to IP blacklist
    is_production = os.environ.get('RENDER') == 'true'
    
    if is_production:
        # On Render: Skip Instagram verification due to IP blacklisting
        # Accept any username and create mock profile
        print(f"[LOOKUP] ⚠️ Production mode: Bypassing Instagram API (IP blacklisted)")
        session['target_username'] = username
        
        return jsonify({
            'success': True,
            'profile': {
                'username': username,
                'full_name': username.title(),
                'biography': 'Instagram user',
                'follower_count': 0,
                'following_count': 0,
                'profile_pic_url': 'https://via.placeholder.com/150',
                'is_verified': False,
                'is_private': False
            }
        })
    
    # Local development: Try to fetch real profile
    try:
        profile_info = ig_automation.get_profile_info(username)
        if not profile_info:
            return jsonify({'success': False, 'error': 'Profile not found'}), 404
        
        # Store username in session for later claim
        session['target_username'] = username
        
        print(f"[LOOKUP] ✓ Profile found: @{username}")
        return jsonify({
            'success': True,
            'profile': profile_info
        })
    except Exception as e:
        print(f"[LOOKUP] ✗ Error: {str(e)}")
        # Fallback: Accept username anyway
        session['target_username'] = username
        return jsonify({
            'success': True,
            'profile': {
                'username': username,
                'full_name': username.title(),
                'biography': 'Instagram user',
                'follower_count': 0,
                'following_count': 0,
                'profile_pic_url': 'https://via.placeholder.com/150',
                'is_verified': False,
                'is_private': False
            }
        })

@app.route('/claim')
def claim_page():
    """Claim page - shows profile and claim/credit button"""
    user = get_or_create_user()
    
    # Get target username from session
    target_username = session.get('target_username')
    if not target_username:
        return redirect(url_for('index'))
    
    # Check if already used free test
    if user.free_test_used:
        # Show "already claimed" with credit option
        return render_template('claim.html', 
                             username=target_username,
                             is_authenticated=user.is_authenticated,
                             already_claimed=True,
                             has_credits=user.free_targets > 0,
                             credits_count=user.free_targets,
                             credits_followers=user.free_targets * 30)
    
    return render_template('claim.html', 
                         username=target_username,
                         is_authenticated=user.is_authenticated,
                         already_claimed=False)

@app.route('/api/signup', methods=['POST'])
def signup():
    """Simplified signup - email only"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email required'}), 400
    
    # Check if email is already used by another user
    from models import User
    existing_user = User.query.filter_by(email=email).first()
    
    if existing_user:
        # Log in as existing user
        session['user_id'] = existing_user.session_id
        session['demo_mode'] = False
        existing_user.is_authenticated = True
        db.session.commit()
        print(f"[AUTH] User logged in: {email}")
        return jsonify({
            'success': True,
            'message': 'Welcome back! You can now claim your free followers.',
            'email': email
        })
    
    # Update current user with new email
    user = get_or_create_user()
    user.email = email
    user.is_authenticated = True
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] Signup error: {str(e)}")
        return jsonify({'success': False, 'error': 'Could not create account. Please try again.'}), 500
    
    session['demo_mode'] = False
    
    print(f"[AUTH] User signed up: {email}")
    
    return jsonify({
        'success': True,
        'message': 'Account created! You can now claim your free followers.',
        'email': email
    })

@app.route('/api/claim-free-followers', methods=['POST'])
def claim_free_followers():
    """Simplified claim endpoint - uses stored username from session"""
    user = get_or_create_user()
    
    # Check if user is authenticated
    if not user.is_authenticated:
        return jsonify({'success': False, 'error': 'Please sign up first', 'requires_auth': True}), 401
    
    # Check if user already used free test
    if user.free_test_used:
        return jsonify({'success': False, 'error': 'You have already claimed your free followers'}), 400
    
    # Get target username from session
    target_username = session.get('target_username')
    if not target_username:
        return jsonify({'success': False, 'error': 'No target username found. Please start over.'}), 400
    
    # Check if target already used
    existing_target = Target.query.filter_by(username=target_username).first()
    if existing_target:
        return jsonify({'success': False, 'error': f'Target @{target_username} has already been used'}), 400
    
    # Check if enough unused accounts
    unused_count = DonatedAccount.query.filter_by(status='unused').count()
    if unused_count < 1:
        return jsonify({'success': False, 'error': f'System temporarily unavailable. No donor accounts available.'}), 400
    
    # Mark user as using free test
    user.free_test_used = True
    
    # Create target record
    target = Target(username=target_username, tier='free_test', user_id=user.id)
    db.session.add(target)
    
    # Get all unused accounts for the job
    unused_accounts = DonatedAccount.query.filter_by(status='unused').all()
    accounts_data = [
        {'username': acc.username, 'password': acc.password, 'id': acc.id}
        for acc in unused_accounts
    ]
    
    # Create job for Hands worker
    job = Job(
        job_type='follow',
        target_username=target_username,
        tier='free_test',
        user_id=user.id,
        payload={'accounts': accounts_data}
    )
    db.session.add(job)
    db.session.commit()
    
    print(f"[CLAIM] User {user.email} claimed free followers for @{target_username}")
    print(f"[CLAIM] Created job #{job.id} with {len(accounts_data)} accounts")
    
    return jsonify({'success': True, 'message': 'Job queued. Waiting for worker...', 'target': target_username, 'job_id': job.id})

@app.route('/api/donate', methods=['POST'])
def donate_account():
    """Donate Instagram account"""
    # Check if user is authenticated
    if is_demo_mode():
        return jsonify({'success': False, 'error': 'Please sign up to donate real accounts', 'requires_auth': True}), 401
    
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    print(f"\n[DONATE] Donation request for @{username}")
    
    if not username or not password:
        print(f"[DONATE] ✗ Missing credentials")
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    # Check if account already donated
    existing = DonatedAccount.query.filter_by(username=username).first()
    if existing:
        print(f"[DONATE] ✗ Account already donated")
        return jsonify({'success': False, 'error': 'This account has already been donated'}), 400
    
    # Get current user
    user = get_or_create_user()
    
    # Check if running locally (ig_automation available) or production (job-based)
    is_local = os.environ.get('RENDER') != 'true'
    
    if is_local:
        # Local dev: verify directly
        print(f"[DONATE] [LOCAL] Verifying account with Instagram...")
        success, message = ig_automation.verify_account(username, password)
        if not success:
            print(f"[DONATE] ✗ Verification failed: {message}")
            return jsonify({'success': False, 'error': message}), 400
        
        # Save account
        print(f"[DONATE] ✓ Verification successful, saving to database...")
        account = DonatedAccount(username=username, password=password, user_id=user.id)
        db.session.add(account)
        user.free_targets += 1
        db.session.commit()
        print(f"[DONATE] ✓ Account saved. User now has {user.free_targets} free target(s)")
        
        return jsonify({
            'success': True,
            'message': f'Account @{username} donated successfully! You now have {user.free_targets} free target(s).',
            'free_targets': user.free_targets
        })
    else:
        # Production: create verification job
        print(f"[DONATE] [PRODUCTION] Creating verification job")
        job = Job(
            job_type='verify',
            user_id=user.id,
            payload={'username': username, 'password': password}
        )
        db.session.add(job)
        db.session.commit()
        print(f"[DONATE] ✓ Created verification job #{job.id}")
        
        return jsonify({
            'success': True,
            'message': f'Verifying account @{username}... Please wait.',
            'job_id': job.id,
            'pending': True
        })

@app.route('/api/remove-account/<int:account_id>', methods=['DELETE'])
def remove_account(account_id):
    """Remove a donated account"""
    user = get_or_create_user()
    
    # Check if user is authenticated
    if not user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    # Get account
    account = DonatedAccount.query.get(account_id)
    if not account:
        return jsonify({'success': False, 'error': 'Account not found'}), 404
    
    print(f"\n[REMOVE] Removing account @{account.username} (ID: {account_id})")
    
    # Check if account has been used
    if account.status == 'used':
        print(f"[REMOVE] ✗ Account has already been used, cannot remove")
        return jsonify({'success': False, 'error': 'Cannot remove account that has already been used'}), 400
    
    # Delete account
    username = account.username
    db.session.delete(account)
    
    # Decrement user's free targets (if they have any)
    if user.free_targets > 0:
        user.free_targets -= 1
    
    db.session.commit()
    print(f"[REMOVE] ✓ Account @{username} removed successfully")
    
    return jsonify({
        'success': True,
        'message': f'Account @{username} removed successfully'
    })

@app.route('/api/free-test', methods=['POST'])
def free_test():
    """Execute free test (20 followers, once per user)"""
    user = get_or_create_user()
    
    # Check if user is authenticated
    if is_demo_mode():
        return jsonify({'success': False, 'error': 'Please sign up to use the free test', 'requires_auth': True}), 401
    
    # Check if user already used free test
    if user.free_test_used:
        return jsonify({'success': False, 'error': 'You have already used your free test'}), 400
    
    data = request.get_json()
    target_username = data.get('target', '').strip().replace('@', '')
    
    if not target_username:
        return jsonify({'success': False, 'error': 'Target username required'}), 400
    
    # Check if target already used
    existing_target = Target.query.filter_by(username=target_username).first()
    if existing_target:
        return jsonify({'success': False, 'error': f'Target @{target_username} has already been used in {existing_target.tier} lane'}), 400
    
    # Check if enough unused accounts (minimum 1 for testing)
    unused_count = DonatedAccount.query.filter_by(status='unused').count()
    if unused_count < 1:
        return jsonify({'success': False, 'error': f'Not enough donated accounts. Need at least 1, have {unused_count}'}), 400
    
    # Mark user as using free test
    user.free_test_used = True
    
    # Create target record
    target = Target(username=target_username, tier='free_test', user_id=user.id)
    db.session.add(target)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Starting free test...', 'target': target_username})

@app.route('/api/donation-boost', methods=['POST'])
def donation_boost():
    """Execute donation boost (30 followers per donated account)"""
    user = get_or_create_user()
    
    # Check if user is authenticated
    if is_demo_mode():
        return jsonify({'success': False, 'error': 'Please sign up to use donation rewards', 'requires_auth': True}), 401
    
    # Check if user has free targets
    if user.free_targets < 1:
        return jsonify({'success': False, 'error': 'You have no free targets. Donate an account to unlock a target.'}), 400
    
    data = request.get_json()
    target_username = data.get('target', '').strip().replace('@', '')
    
    if not target_username:
        return jsonify({'success': False, 'error': 'Target username required'}), 400
    
    # Check if target already used
    existing_target = Target.query.filter_by(username=target_username).first()
    if existing_target:
        return jsonify({'success': False, 'error': f'Target @{target_username} has already been used'}), 400
    
    # Check if enough unused accounts (minimum 1 for testing)
    unused_count = DonatedAccount.query.filter_by(status='unused').count()
    if unused_count < 1:
        return jsonify({'success': False, 'error': f'Not enough donated accounts. Need at least 1, have {unused_count}'}), 400
    
    # Decrement user's free targets
    user.free_targets -= 1
    
    # Create target record
    target = Target(username=target_username, tier='donation', user_id=user.id)
    db.session.add(target)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Starting donation boost...', 'target': target_username, 'free_targets': user.free_targets})

@app.route('/api/use-credit', methods=['POST'])
def use_credit():
    """Use earned credit to boost a target (30 followers)"""
    user = get_or_create_user()
    
    # Check if user is authenticated
    if not user.is_authenticated:
        return jsonify({'success': False, 'error': 'Please sign up to use credits', 'requires_auth': True}), 401
    
    # Check if user has credits
    if user.free_targets < 1:
        return jsonify({'success': False, 'error': 'You have no credits. Donate accounts to earn credits!'}), 400
    
    # Get target username from session
    target_username = session.get('target_username')
    if not target_username:
        return jsonify({'success': False, 'error': 'No target username found. Please start over.'}), 400
    
    # Check if target already used
    existing_target = Target.query.filter_by(username=target_username).first()
    if existing_target:
        return jsonify({'success': False, 'error': f'Target @{target_username} has already been boosted'}), 400
    
    # Check if enough unused accounts
    unused_count = DonatedAccount.query.filter_by(status='unused').count()
    if unused_count < 1:
        return jsonify({'success': False, 'error': 'System temporarily unavailable. No donor accounts available.'}), 400
    
    # Decrement user's credits
    user.free_targets -= 1
    
    # Create target record
    target = Target(username=target_username, tier='donation', user_id=user.id)
    db.session.add(target)
    
    # Get all unused accounts for the job
    unused_accounts = DonatedAccount.query.filter_by(status='unused').all()
    accounts_data = [
        {'username': acc.username, 'password': acc.password, 'id': acc.id}
        for acc in unused_accounts
    ]
    
    # Create job for Hands worker
    job = Job(
        job_type='follow',
        target_username=target_username,
        tier='donation',
        user_id=user.id,
        payload={'accounts': accounts_data}
    )
    db.session.add(job)
    db.session.commit()
    
    print(f"[CREDIT] User {user.email} used credit for @{target_username}. Remaining credits: {user.free_targets}")
    print(f"[CREDIT] Created job #{job.id} with {len(accounts_data)} accounts")
    
    return jsonify({
        'success': True, 
        'message': 'Job queued. Waiting for worker...', 
        'target': target_username,
        'credits_remaining': user.free_targets,
        'job_id': job.id
    })

# ============================================================================
# INTERNAL API (for Hands Worker)
# ============================================================================

def require_hands_api_key(f):
    """Decorator to require Hands API key authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Hands-API-Key')
        if not api_key or api_key != app.config['HANDS_API_KEY']:
            print(f"[INTERNAL] ✗ Unauthorized request - invalid API key")
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/internal/poll-jobs', methods=['GET'])
@require_hands_api_key
def poll_jobs():
    """Poll for pending jobs (called by Hands worker)"""
    # Get oldest pending job
    job = Job.query.filter_by(status='pending').order_by(Job.created_at.asc()).first()
    
    if not job:
        return '', 204  # No content
    
    # Mark job as processing
    job.status = 'processing'
    job.started_at = datetime.utcnow()
    db.session.commit()
    
    print(f"[INTERNAL] ✓ Job #{job.id} ({job.job_type}) sent to Hands")
    
    # Return job data
    return jsonify({
        'job': {
            'id': job.id,
            'job_type': job.job_type,
            'target_username': job.target_username,
            'tier': job.tier,
            'payload': job.payload
        }
    })

@app.route('/internal/progress', methods=['POST'])
@require_hands_api_key
def job_progress():
    """Receive progress updates from Hands worker"""
    data = request.get_json()
    job_id = data.get('job_id')
    current = data.get('current')
    total = data.get('total')
    status_msg = data.get('status')
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    # Emit Socket.IO progress to user's browser
    socketio.emit('progress', {
        'current': current,
        'total': total,
        'status': status_msg
    })
    
    print(f"[INTERNAL] Progress for job #{job_id}: {current}/{total} - {status_msg}")
    
    return jsonify({'success': True})

@app.route('/internal/job-complete', methods=['POST'])
@require_hands_api_key
def job_complete():
    """Mark job as complete (called by Hands worker)"""
    data = request.get_json()
    job_id = data.get('job_id')
    status = data.get('status')  # 'complete' or 'failed'
    result = data.get('result')
    error = data.get('error')
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    # Update job status
    job.status = status
    job.completed_at = datetime.utcnow()
    job.result = result
    if error:
        job.error = error
    
    db.session.commit()
    
    # Emit Socket.IO completion to user's browser
    if status == 'complete':
        socketio.emit('complete', {
            'success': True,
            'results': result
        })
        print(f"[INTERNAL] ✓ Job #{job_id} completed successfully")
    else:
        socketio.emit('complete', {
            'success': False,
            'error': error or 'Job failed'
        })
        print(f"[INTERNAL] ✗ Job #{job_id} failed: {error}")
    
    return jsonify({'success': True})

# ============================================================================
# SOCKET.IO (Real-time updates)
# ============================================================================

@socketio.on('execute_follows')
def handle_execute_follows(data):
    """Execute follow actions with real-time updates"""
    target_username = data.get('target')
    tier = data.get('tier')
    
    print(f"\n[WEBSOCKET] Received execute_follows request")
    print(f"[WEBSOCKET] Target: @{target_username}, Tier: {tier}")
    
    # Use available account count (for testing with minimal accounts)
    from models import DonatedAccount
    available = DonatedAccount.query.filter_by(status='unused').count()
    
    if tier == 'free_test':
        count = min(available, 20)  # Use up to 20 or whatever is available
    else:
        count = min(available, 30)  # Use up to 30 or whatever is available
    
    emit('progress', {'current': 0, 'total': count, 'status': 'Initializing...'})
    
    # Execute follows
    print(f"[WEBSOCKET] Starting follow execution via instagrapi...")
    success, result = ig_automation.execute_follows(target_username, tier, count, socketio)
    
    if not success:
        print(f"[WEBSOCKET] ✗ Execution failed: {result}")
        emit('complete', {'success': False, 'error': result})
    else:
        print(f"[WEBSOCKET] ✓ Execution completed successfully")
        emit('complete', {
            'success': True,
            'results': result
        })

@app.route('/admin')
def admin_login():
    """Admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/verify', methods=['POST'])
def admin_verify():
    """Verify admin password"""
    data = request.get_json()
    password = data.get('password', '')
    
    if password == app.config['ADMIN_PASSWORD']:
        session['admin'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid password'}), 401

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard (private)"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    # Get all data
    accounts = DonatedAccount.query.order_by(DonatedAccount.donated_at.desc()).all()
    targets = Target.query.order_by(Target.created_at.desc()).all()
    logs = ActionLog.query.order_by(ActionLog.timestamp.desc()).limit(100).all()
    
    # Stats
    stats = {
        'total_accounts': DonatedAccount.query.count(),
        'unused_accounts': DonatedAccount.query.filter_by(status='unused').count(),
        'used_accounts': DonatedAccount.query.filter_by(status='used').count(),
        'total_targets': Target.query.count(),
        'free_test_targets': Target.query.filter_by(tier='free_test').count(),
        'donation_targets': Target.query.filter_by(tier='donation').count(),
        'total_actions': ActionLog.query.count(),
        'successful_actions': ActionLog.query.filter_by(result='success').count(),
    }
    
    return render_template('admin_dashboard.html', 
                         accounts=accounts, 
                         targets=targets, 
                         logs=logs,
                         stats=stats)

@app.route('/admin/add-account', methods=['POST'])
def admin_add_account():
    """Admin endpoint to add donor accounts directly"""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    print(f"\n[ADMIN] Adding donor account @{username}")
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    # Check if account already exists
    existing = DonatedAccount.query.filter_by(username=username).first()
    if existing:
        return jsonify({'success': False, 'error': f'Account @{username} already exists'}), 400
    
    # Verify Instagram credentials
    try:
        is_valid = ig_automation.verify_account(username, password)
        if not is_valid:
            print(f"[ADMIN] ✗ Invalid credentials for @{username}")
            return jsonify({'success': False, 'error': 'Invalid Instagram credentials'}), 400
    except Exception as e:
        print(f"[ADMIN] ✗ Verification error: {str(e)}")
        return jsonify({'success': False, 'error': f'Could not verify account: {str(e)}'}), 500
    
    # Add account to pool (no user_id for admin-added accounts)
    account = DonatedAccount(username=username, password=password, user_id=None)
    db.session.add(account)
    db.session.commit()
    
    print(f"[ADMIN] ✓ Account @{username} added to pool")
    
    return jsonify({
        'success': True,
        'message': f'Account @{username} added to donor pool',
        'account': {
            'id': account.id,
            'username': account.username,
            'status': account.status,
            'donated_at': account.donated_at.isoformat()
        }
    })

@app.route('/admin/remove-account/<int:account_id>', methods=['POST'])
def admin_remove_account(account_id):
    """Remove bad account"""
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    account = DonatedAccount.query.get(account_id)
    if not account:
        return jsonify({'success': False, 'error': 'Account not found'}), 404
    
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Account @{account.username} removed'})

@app.route('/admin/logout')
def admin_logout():
    """Logout admin"""
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/api/demo-action', methods=['POST'])
def demo_action():
    """Simulate actions in demo mode"""
    data = request.get_json()
    action_type = data.get('type')  # 'donate', 'free_test', 'donation_boost'
    
    if not is_demo_mode():
        return jsonify({'success': False, 'error': 'Not in demo mode'}), 400
    
    # Return simulated success
    if action_type == 'donate':
        return jsonify({
            'success': True,
            'demo': True,
            'message': 'Demo: Account donation simulated!',
            'free_targets': 1
        })
    elif action_type in ['free_test', 'donation_boost']:
        return jsonify({
            'success': True,
            'demo': True,
            'message': f'Demo: {action_type} simulation started',
            'target': data.get('target', 'demo_target')
        })
    
    return jsonify({'success': False, 'error': 'Unknown action type'}), 400

@app.route('/system-status')
def system_status():
    """Serve system status page"""
    return send_from_directory('.', 'system_status.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
