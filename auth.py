# --- START OF FILE auth.py ---

import sqlite3
import logging
import os
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

USERS_DB_PATH = None  # Will be set by initialize_auth_db

def initialize_auth_db(base_dir):
    """Initializes the path for users.db and creates the table if it doesn't exist."""
    global USERS_DB_PATH
    if USERS_DB_PATH is None: # Initialize only once
        USERS_DB_PATH = os.path.join(base_dir, 'users.db')
        logger.info(f"User authentication database path set to: {USERS_DB_PATH}")
    
    # Ensure the directory for the database exists
    db_directory = os.path.dirname(USERS_DB_PATH)
    if not os.path.exists(db_directory) and db_directory: # Check if db_directory is not an empty string
        try:
            os.makedirs(db_directory, exist_ok=True)
            logger.info(f"Created directory for user database: {db_directory}")
        except OSError as e:
            logger.error(f"Could not create directory {db_directory} for user database: {e}")
            raise # Critical error if directory cannot be made

    _create_user_table_if_not_exists()


def _get_users_db_connection():
    """Establishes a connection to the users.db."""
    if USERS_DB_PATH is None:
        logger.critical("USERS_DB_PATH is not initialized. Call initialize_auth_db from app.py first.")
        raise RuntimeError("User database path not configured. This is a critical setup error.")
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"User database connection error to {USERS_DB_PATH}: {e}")
        raise # Re-raise to indicate a problem

def _create_user_table_if_not_exists():
    """Creates the users table in users.db if it doesn't exist."""
    conn = None
    try:
        conn = _get_users_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, 
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logger.info("Users table in users.db checked/created successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating users table in users.db: {e}")
        # Not raising here to allow app to potentially start if other parts are okay,
        # but logging severe error. Health check will report this.
    except RuntimeError as e: # From _get_users_db_connection if path is None
         logger.error(f"Runtime error during user table creation: {e}")
    finally:
        if conn:
            conn.close()

def register_user(name, email, password):
    """Registers a new user in users.db."""
    hashed_password = generate_password_hash(password)
    conn = None
    try:
        conn = _get_users_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        logger.info(f"User {name} (ID: {user_id}) registered successfully in users.db.")
        return user_id
    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation for email
        logger.warning(f"Email already exists in users.db: {email}.")
        return None 
    except (sqlite3.Error, RuntimeError) as e:
        logger.error(f"Database error registering user {name} in users.db: {e}")
        return None 
    finally:
        if conn:
            conn.close()

def login_user(email, password):
    """
    Logs in a user by email and password from users.db.
    Returns user dict if successful, None otherwise.
    """
    user = None
    conn = None
    try:
        conn = _get_users_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_data = cursor.fetchone()

        if user_data and check_password_hash(user_data['password_hash'], password):
            user = dict(user_data) 
            logger.info(f"User {user['name']} (Email: {email}) logged in successfully from users.db.")
            return user
        else:
            logger.warning(f"Login failed for email from users.db: {email}")
            return None
    except (sqlite3.Error, RuntimeError) as e:
        logger.error(f"Database error during login for {email} from users.db: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """Retrieves a user by their ID from users.db."""
    conn = None
    try:
        conn = _get_users_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        return dict(user_data) if user_data else None
    except (sqlite3.Error, RuntimeError) as e:
        logger.error(f"Database error fetching user by ID {user_id} from users.db: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_email(email):
    """Retrieves a user by their email from users.db."""
    conn = None
    try:
        conn = _get_users_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_data = cursor.fetchone()
        return dict(user_data) if user_data else None
    except (sqlite3.Error, RuntimeError) as e:
        logger.error(f"Database error fetching user by email {email} from users.db: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_users():
    """Retrieves all users from users.db. For admin purposes. Excludes password_hash."""
    conn = None
    users = []
    try:
        conn = _get_users_db_connection()
        cursor = conn.cursor()
        # Select all relevant fields EXCEPT password_hash
        cursor.execute("SELECT id, name, email, created_at FROM users ORDER BY created_at DESC")
        user_rows = cursor.fetchall()
        for row in user_rows:
            users.append(dict(row))
        logger.info(f"Fetched {len(users)} users for admin page.")
        return users
    except (sqlite3.Error, RuntimeError) as e:
        logger.error(f"Database error fetching all users from users.db: {e}")
        return [] # Return empty list on error
    finally:
        if conn:
            conn.close()
# --- END OF FILE auth.py ---