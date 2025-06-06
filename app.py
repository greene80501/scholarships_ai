# --- START OF FILE app.py ---

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, flash, g
import sqlite3
import os
import json
import logging
from datetime import datetime
from functools import wraps # For login_required decorator

# Import modularized components
import ai_advisor # Import the module itself
from search_utils import (
    api_search_scholarships,
    get_scholarship_detail_by_id,
    get_application_stats,
    ScholarshipDatabase
)
import auth # Import the new auth module

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Flask App Setup ---
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCHOLARSHIPS_DATABASE_PATH = os.path.join(BASE_DIR, 'scholarships.db') # Path for scholarship data
# User database path will be managed by auth.py, initialized below
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_very_secret_key_for_dev_only_change_me") # IMPORTANT: Set a strong secret key in production

ADMIN_EMAIL = "greene.wyatt30@gmail.com" # Admin user email

# --- Database Initialization ---
# Scholarship DB
scholarships_db = ScholarshipDatabase(SCHOLARSHIPS_DATABASE_PATH)

# User Auth DB - Initialize auth module, which handles its own DB (users.db)
with app.app_context():
    try:
        auth.initialize_auth_db(BASE_DIR) # Pass base_dir for auth.py to construct its DB path
    except Exception as e:
        logger.error(f"Failed to initialize user authentication database: {e}")


# --- Initialize RAG System at Startup (from ai_advisor.py) ---
ai_advisor.initialize_rag_system_on_startup(BASE_DIR) # RAG system uses its own data dir
logger.info(f"RAG system initialization status after startup call: {ai_advisor.RAG_INITIALIZED_SUCCESSFULLY}")


# --- User Session Management & Decorators ---
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = auth.get_user_by_id(user_id) # auth.py uses its own DB connection

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash("You need to be logged in to access this page.", "info")
            return redirect(url_for('login_route', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- HTML Serving Routes ---
@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/search.html')
def search_page():
    return render_template('search.html')

@app.route('/ai-recommend.html')
@login_required 
def ai_recommend_page():
    return render_template('ai-recommend.html')

@app.route('/bookmarks.html')
@login_required
def bookmarks_page():
    return render_template('bookmarks.html')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if g.user:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email'] 
        password = request.form['password']
        user = auth.login_user(email, password) # Uses users.db via auth.py
        if user:
            session.clear()
            session['user_id'] = user['id']
            session['name'] = user['name'] 
            flash(f"Welcome back, {user['name']}!", 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if g.user:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['name'] 
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not name.strip():
            flash('Name is required.', 'error')
            return render_template('register.html', name=name, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html', name=name, email=email)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('register.html', name=name, email=email)

        if auth.get_user_by_email(email): # Uses users.db via auth.py
            flash('Email address already registered. Please use a different one or login.', 'error')
            return render_template('register.html', name=name, email=email)

        user_id = auth.register_user(name, email, password) # Uses users.db via auth.py
        if user_id:
            session.clear()
            session['user_id'] = user_id
            session['name'] = name 
            flash('Account created successfully! You are now logged in.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Registration failed. Email might already be in use, or a database error occurred.', 'error')
            return render_template('register.html', name=name, email=email)
            
    return render_template('register.html')

@app.route('/logout')
def logout_route():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_route'))

@app.route('/admin')
@login_required
def admin_page():
    # Ensure g.user is not None and 'email' key exists before checking its value
    if g.user is None or 'email' not in g.user or g.user['email'] != ADMIN_EMAIL:
        logger.warning(f"Unauthorized access attempt to admin page by user: {g.user.get('email') if g.user else 'Guest'}")
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for('index'))

    all_users = auth.get_all_users()
    logger.info(f"Admin user {g.user['email']} accessed admin page. Displaying {len(all_users)} users.")
    return render_template('admin.html', users=all_users)


# --- API Routes ---
@app.route('/api/ai/chat', methods=['POST'])
@api_login_required 
def api_ai_chat_route():
    if not ai_advisor.RAG_INITIALIZED_SUCCESSFULLY:
        logger.warning("AI Chat: RAG system not initialized or failed, AI chat unavailable.")
        return jsonify({
            "ai_response": "I'm sorry, my AI advisory capabilities are currently unavailable. Please try again later.",
            "scholarships": []
        }), 503
    
    data = request.json
    user_message = data.get('message', '').strip()
    conversation_history_from_client = data.get('conversation_history', [])

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    ai_response, scholarships_to_send, updated_history = ai_advisor.handle_ai_chat(
        user_message,
        conversation_history_from_client,
        scholarships_db # Pass scholarships_db for querying scholarship data
    )
    
    return jsonify({
        "ai_response": ai_response,
        "scholarships": scholarships_to_send,
        "conversation_history": updated_history
    })

@app.route('/api/search')
def api_search_route():
    return api_search_scholarships(request.args, scholarships_db) # Uses scholarships_db

@app.route('/api/scholarship/<int:scholarship_id>')
def api_scholarship_detail_route(scholarship_id):
    return get_scholarship_detail_by_id(scholarship_id, scholarships_db) # Uses scholarships_db

@app.route('/api/stats')
def api_stats_route():
    return get_application_stats(scholarships_db) # Uses scholarships_db

# --- Static File Serving (Favicon as an example, CSS/JS handled by static_folder) ---
@app.route('/favicon.ico')
def favicon():
    favicon_path = os.path.join(app.static_folder, 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    return '', 204

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 Not Found: {request.url} - {error}")
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Resource not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

# --- Health Check ---
@app.route('/health')
def health_check():
    # Scholarship DB Check
    scholarships_db_healthy = False
    scholarships_db_error_message = None
    try:
        conn_s = scholarships_db.get_connection()
        conn_s.execute("SELECT 1") 
        conn_s.close()
        scholarships_db_healthy = True
    except Exception as e:
        scholarships_db_error_message = str(e)
        logger.error(f"Health check Scholarship DB error: {e}")

    # Users DB Check
    users_db_healthy = False
    users_db_error_message = None
    if auth.USERS_DB_PATH: # Check if auth module DB path is set
        try:
            conn_u = auth._get_users_db_connection() # Use internal getter from auth
            cursor_u = conn_u.cursor()
            cursor_u.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
            if cursor_u.fetchone():
                users_db_healthy = True
            else:
                users_db_error_message = "Users table not found in users.db."
            conn_u.close()
        except Exception as e:
            users_db_error_message = str(e)
            logger.error(f"Health check Users DB error: {e}")
    else:
        users_db_error_message = "User DB path not initialized in auth module."
        logger.error(users_db_error_message)


    rag_initialized = ai_advisor.RAG_INITIALIZED_SUCCESSFULLY
    rag_status_message = 'RAG system initialized.' if rag_initialized else 'RAG system failed to initialize.'
    if not rag_initialized:
         logger.warning(f"Health check RAG status: {rag_status_message}")

    overall_healthy = scholarships_db_healthy and users_db_healthy and rag_initialized
    status_code = 200 if overall_healthy else 503
    
    return jsonify({
        'status': 'healthy' if overall_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + "Z",
        'version': '1.1.2', # Incremented version
        'dependencies': {
            'scholarships_database': {
                'status': 'ok' if scholarships_db_healthy else 'error',
                'message': scholarships_db_error_message if scholarships_db_error_message else 'Connected successfully.'
            },
            'users_database': {
                'status': 'ok' if users_db_healthy else 'error',
                'message': users_db_error_message if users_db_error_message else 'Connected successfully and users table exists.'
            },
            'rag_system': {
                'status': 'ok' if rag_initialized else 'error',
                'message': rag_status_message
            }
        }
    }), status_code

# --- Main Application Execution ---
if __name__ == '__main__':
    logger.info("Starting ScholarshipHub application...")
    logger.info(f"Scholarships Database location: {SCHOLARSHIPS_DATABASE_PATH}")
    if auth.USERS_DB_PATH:
        logger.info(f"Users Database location: {auth.USERS_DB_PATH}")
    else: # Should not happen if initialize_auth_db was successful
        logger.error("Users Database path (auth.USERS_DB_PATH) is not set. Check initialization.")


    static_dir_path = os.path.join(BASE_DIR, app.static_folder)
    rag_data_dir = os.path.join(BASE_DIR, "data")
    rag_persist_dir = os.path.join(BASE_DIR, "storage_ai_advisor")

    for dir_path in [static_dir_path, rag_data_dir, rag_persist_dir]:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
                if dir_path == rag_data_dir and not os.listdir(rag_data_dir):
                    with open(os.path.join(rag_data_dir, "placeholder.txt"), "w") as f:
                        f.write("This is a placeholder for scholarship data. Please replace with actual data.\n")
                    logger.info(f"Created placeholder.txt in {rag_data_dir}.")
            except OSError as e:
                logger.error(f"Could not create directory {dir_path}: {e}")

    app.run(
        debug=os.environ.get("FLASK_DEBUG", "True").lower() == "true",
        host=os.environ.get("FLASK_RUN_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_RUN_PORT", 5000)),
        threaded=True
    )
# --- END OF FILE app.py ---