import os
import secrets
from datetime import datetime
import pytz
import bcrypt
from typing import Optional, Dict, Tuple
from bson.objectid import ObjectId
import logging
from logging.handlers import RotatingFileHandler
from flask import request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import re

IST = pytz.timezone('Asia/Kolkata')

def setup_logger(name: str = 'app'):
    """
    Configure and return a logger instance with file and console handlers.
    
    Args:
        name (str): Name of the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Remove existing handlers to prevent duplicate logging
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file path
    log_file = os.path.join(log_dir, 'app.log')

    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024*1024*5,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    # Get logger instance
    logger = logging.getLogger(name)
    return logger

# Initialize the main application logger
logger = setup_logger()

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.full_name = user_data.get('full_name', '')
        self.avatar_url = generate_letter_avatar(self.full_name)
        self.roles = user_data.get('roles', ['user'])
        self.is_active = user_data.get('is_active', True)
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.is_active

    def is_anonymous(self):
        return False

    def get_roles(self):
        return self.roles

    def name(self):
        return self.full_name or self.email.split('@')[0]

    def username(self):
        return self.email.split('@')[0]

    def get_avatar(self):
        return self.avatar_url

    def update_last_login(self, db_manager):
        """Update user's last login time"""
        try:
            current_time = datetime.now(IST)
            db_manager.users.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': {'last_login': current_time}}
            )
            self.last_login = current_time
        except Exception as e:
            logger.error(f"Failed to update login for {self.id}: {e}")

    def refresh(self, db_manager):
        """Refresh user data from database"""
        try:
            user_data = db_manager.users.find_one({'_id': ObjectId(self.id)})
            if user_data:
                self.email = user_data['email']
                self.full_name = user_data.get('full_name', '')
                self.avatar_url = generate_letter_avatar(self.full_name)
                self.roles = user_data.get('roles', ['user'])
                self.is_active = user_data.get('is_active', True)
                self.created_at = user_data.get('created_at')
                self.last_login = user_data.get('last_login')
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to refresh user data for {self.id}: {e}")
            return False

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address with comprehensive checks.
    
    Args:
        email: Email address to validate
    
    Returns:
        Tuple of (is_valid, message)
    """
    # Check if email is empty or None
    if not email or not isinstance(email, str):
        return False, "Email cannot be empty"
    
    # Basic regex pattern for email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Check regex pattern
    if not re.match(email_regex, email):
        return False, "Invalid email format"
    return True, "Valid email"

def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Args:
        password (str): Password to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    # Password requirements:
    # - At least 8 characters
    # - At least one uppercase letter
    # - At least one lowercase letter
    # - At least one digit
    # - At least one special character
    password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.match(password_pattern, password):
        return False, "Password must include uppercase, lowercase, number, and special character"
    
    return True, ""

def validate_login_credentials(email: str, password: str, db_manager) -> Optional[Dict]:
    """
    Validate user login credentials.
    
    Args:
        email (str): User's email
        password (str): User's password
        db_manager: Database manager instance
    
    Returns:
        dict: User document if credentials are valid, None otherwise
    """
    try:
        # Input validation
        email_valid, email_error = validate_email(email)
        if not email_valid:
            logger.warning(f"Invalid email format: {email_error}")
            return None
        
        # Find user by email
        user = db_manager.users.find_one({'email': email.lower()})
        
        if not user:
            logger.warning(f"No user found with email: {email}")
            return None
        
        # Check if account is locked
        if user.get('account_locked', False):
            logger.warning(f"Account locked for user: {email}")
            return None
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            logger.warning(f"Invalid password for user: {email}")
            return None
        
        return user
    except Exception as e:
        logger.error(f"Login validation error: {e}")
        return None

def create_user(user_data: dict, db_manager) -> Optional[str]:
    """
    Create a new user with comprehensive validation and generate avatar URL.
    
    Args:
        user_data (dict): User registration details
        db_manager: Database manager instance
    
    Returns:
        str: Inserted user ID or None if creation fails
    """
    try:
        # Validate email
        email_valid, email_error = validate_email(user_data['email'])
        if not email_valid:
            logger.warning(f"Invalid email during signup: {email_error}")
            return None
        
        # Validate password
        password_valid, password_error = validate_password(user_data['password'])
        if not password_valid:
            logger.warning(f"Invalid password during signup: {password_error}")
            return None
        
        # Check if email already exists
        if db_manager.users.find_one({'email': user_data['email'].lower()}):
            logger.warning(f"Email already exists: {user_data['email']}")
            return None
        
        # Hash password
        hashed_password = bcrypt.hashpw(
            user_data['password'].encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Prepare user data
        user_data = {
            'email': user_data['email'].lower(),
            'password': hashed_password,
            'full_name': user_data.get('full_name', ''),
            'is_active': True,
            'created_at': datetime.now(IST),
            'last_login': datetime.now(IST),
            'avatar_url': generate_letter_avatar(user_data.get('full_name', '')),
            'roles': ['user']
        }
        
        # Insert user
        result = db_manager.users.insert_one(user_data)
        
        if result.inserted_id:
            logger.info(f"User created successfully: {user_data['email']}")
            return str(result.inserted_id)
        
        logger.error("Failed to insert user document")
        return None
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None

def get_auth_context(db_manager, user=None) -> Dict:
    """
    Retrieve the authentication context for the current user.
    
    Args:
        db_manager: Database manager instance
        user: User instance (optional)
        
    Returns:
        dict: A comprehensive authentication context
    """
    try:
        if not user:
            return {
                'is_authenticated': False,
                'user': None
            }
        
        user_data = {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'avatar_url': user.avatar_url,
            'roles': user.roles
        }
        
        return {
            'is_authenticated': True,
            'user': user_data
        }
    except Exception as e:
        logger.error(f"Error getting auth context: {e}")
        return {
            'is_authenticated': False,
            'error': str(e)
        }

def load_user(user_id: str, db_manager) -> Optional[User]:
    """
    Load user from database.
    
    Args:
        user_id (str): User ID
        
    Returns:
        User or None: User instance if found, None otherwise
    """
    try:
        user_data = db_manager.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
        return None
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None

def datetimeformat(value: datetime) -> str:
    """
    Format datetime object for display.
    
    Args:
        value (datetime): Datetime object
        
    Returns:
        str: Formatted datetime string
    """
    return value.strftime('%Y-%m-%d %H:%M:%S')

def timeformat(value: datetime) -> str:
    """
    Format time for display.
    
    Args:
        value (datetime): Datetime object
        
    Returns:
        str: Formatted time string
    """
    return value.strftime('%H:%M')

def format_datetime(dt: datetime) -> str:
    """
    Format datetime object to string in IST timezone.
    
    Args:
        dt (datetime): Datetime object
        
    Returns:
        str: Formatted datetime string
    """
    return dt.astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')

def _handle_error(message: str, status_code: int = 500):
    """
    Handle errors with proper response formatting.
    
    Args:
        message (str): Error message
        status_code (int): HTTP status code
        
    Returns:
        Response: Error response
    """
    if request.is_json:
        return {
            'status': 'error',
            'message': message
        }, status_code
    else:
        flash(message, 'error')
        return redirect(url_for('dashboard'))

def generate_letter_avatar(text: str) -> str:
    """Generate a letter-based avatar URL with proper color contrast.
    
    Args:
        text: Text to convert to avatar
        
    Returns:
        str: Avatar URL with proper color contrast
    """
    if not text:
        return "https://ui-avatars.com/api/?name=U&background=2563eb&color=ffffff"
    
    # Get first letter of text
    first_letter = text[0].upper()
    
    # Generate random background color with good contrast
    colors = [
        "2563eb", "10b981", "3b82f6", "dc2626",  # Primary colors
        "f59e0b", "8b5cf6", "16a34a", "db2777"   # Secondary colors
    ]
    bg_color = colors[hash(first_letter) % len(colors)]
    
    # Create avatar URL with proper contrast
    return f"https://ui-avatars.com/api/?name={first_letter}&background={bg_color}&color=ffffff&size=64&bold=true&rounded=true"