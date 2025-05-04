import os
from typing import Optional
import secrets
from datetime import datetime, timedelta
import pytz
from flask import Flask, request, render_template, session, jsonify, redirect, url_for
from flask_login import LoginManager, current_user, login_required
from flask_socketio import SocketIO, emit
from bson import ObjectId
import logging
import logging.handlers
from dotenv import load_dotenv
from database import db_manager
from chat import process_message_with_llm
from context_tracker import ContextTracker
from auth import (
    load_user, generate_letter_avatar, logger,
    datetimeformat, timeformat, get_auth_context
)
from models import DiseaseParameterWorkflow, DISEASE_PARAMETERS, get_predictor, validate_all_parameters

IST = pytz.timezone('Asia/Kolkata')

# Load environment variables
load_dotenv()

# Configure Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Configure logging
from auth import logger

app.jinja_env.filters['datetimeformat'] = datetimeformat
app.jinja_env.filters['timeformat'] = timeformat
app.jinja_env.filters['generate_letter_avatar'] = generate_letter_avatar

socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

if not db_manager.initialize_db():
    raise Exception("Failed to initialize database")

context_tracker = ContextTracker.initialize(db_manager)

class CustomJSONEncoder:
    def encode(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        from bson.json_util import dumps
        return dumps(obj)

socketio.json_encoder = CustomJSONEncoder()

@login_manager.user_loader
def load_user_callback(user_id):
    return load_user(user_id, db_manager)

@app.context_processor
def inject_auth_context():
    auth_context = get_auth_context(db_manager, current_user if current_user.is_authenticated else None)
    return {'auth_context': auth_context, 'generate_letter_avatar': generate_letter_avatar}

@app.route('/signup', methods=['GET', 'POST'])
def signup():
   
    if request.method == 'POST':
        if request.is_json:
            user_data = request.json
        else:
            user_data = request.form.to_dict()
        user_id = create_user(user_data, db_manager)
        if user_id:
            if request.is_json:
                return {'status': 'success', 'message': 'User registered', 'user_id': user_id}, 201
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        if request.is_json:
            return {'status': 'error', 'message': 'Registration failed'}, 404
        flash('Registration failed. Please check your details.', 'error')
        return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user_data = request.json if request.is_json else request.form.to_dict()
        email, password = user_data.get('email'), user_data.get('password')
        if not email or not password:
            return _handle_login_error("Email and password are required", request.is_json)
        user_data = validate_login_credentials(email, password, db_manager)
        if user_data:
            user = User(user_data)
            login_user(user, remember=True)
            user.update_last_login(db_manager)
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful', 'user': {'email': user.email, 'full_name': user.full_name, 'avatar_url': user.avatar_url}})
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('dashboard'))
        return _handle_login_error("Invalid email or password", request.is_json)
    return render_template('login.html')

def _handle_login_error(message, is_json):
    if is_json:
        return {'status': 'error', 'message': message}, 400
    flash(message, 'error')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

from dashboard_metrics import (
    get_prediction_trends,
    get_most_predicted_conditions,
    calculate_prediction_accuracy
)

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route with user data refresh"""
    if not current_user.refresh(db_manager):
        flash("Failed to refresh user data. Please try logging in again.", "warning")
        return redirect(url_for('login'))
    predictions = db_manager.get_user_predictions(current_user.id)
    metrics = {
        'prediction_trends': get_prediction_trends(current_user.id, db_manager),
        'most_predicted': get_most_predicted_conditions(current_user.id, db_manager),
        'accuracy': calculate_prediction_accuracy(current_user.id, db_manager),
        'total_predictions': len(predictions),
        'recent_predictions': predictions
    }
    return render_template('dashboard.html',
                         user=current_user,
                         metrics=metrics,
                         predictions=predictions)

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', current_user=current_user, user_id=str(current_user.get_id()))

@app.route('/prediction', methods=['GET', 'POST'])
@login_required
def prediction():
    socketio.emit('connect_prediction', {'user_id': str(current_user.id)})
    if request.method == 'POST':
        filters = request.json
        query = {'user_id': str(current_user.id)}
        dt = filters.get('disease_type', '')
        if dt and dt != 'All':
            query['disease_type'] = dt
        sd, ed = filters.get('start_date', ''), filters.get('end_date', '')
        if sd and ed:
            try:
                query['created_at'] = {'$gte': datetime.strptime(sd, '%Y-%m-%d'), '$lte': datetime.strptime(ed, '%Y-%m-%d')}
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
        predictions = list(db_manager.predictions.find(query).sort('created_at', -1).limit(50))
        return jsonify({'status': 'success', 'predictions': [
            {'id': str(p['_id']), 'disease_type': p.get('disease_type', 'Unknown'), 'created_at': p.get('created_at', datetime.utcnow()).isoformat(), 'status': p.get('status', 'pending'), 'result': p.get('result', {})}
            for p in predictions
        ]})
    predictions = list(db_manager.predictions.find({'user_id': str(current_user.id)}).sort('created_at', -1).limit(50))
    return render_template('prediction.html', predictions=[
        {'id': str(p['_id']), 'disease_type': p.get('disease_type', 'Unknown'), 'created_at': p.get('created_at', datetime.utcnow()).isoformat(), 'status': p.get('status', 'pending'), 'result': p.get('result', {})}
        for p in predictions
    ], user=current_user)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        data = {'full_name': request.form.get('full_name'), 'email': request.form.get('email')}
        if data['email'] != current_user.email:
            if not validate_email(data['email'])[0] or db_manager.users.find_one({'email': data['email'], '_id': {'$ne': ObjectId(current_user.id)}}):
                flash('Invalid or duplicate email', 'error')
                return render_template('settings.html')
        if data['full_name'] != current_user.full_name:
            data['avatar_url'] = f'https://api.dicebear.com/6.x/initials/svg?seed={data["full_name"]}&size=64'
        update_data = {k: v for k, v in data.items() if v}
        if update_data and db_manager.users.update_one({'_id': ObjectId(current_user.id)}, {'$set': update_data}).modified_count > 0:
            current_user.refresh()
            flash('Profile updated', 'success')
            return redirect(url_for('dashboard'))
        flash('No changes or update failed', 'error')
    return render_template('settings.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    curr = request.form.get('current_password')
    new = request.form.get('new_password')
    conf = request.form.get('confirm_password')
    if not all([curr, new, conf]):
        flash('All fields required', 'error'); return redirect(url_for('settings'))
    if new != conf:
        flash('Passwords do not match', 'error'); return redirect(url_for('settings'))
    user = db_manager.users.find_one({'_id': ObjectId(current_user.id)})
    if not user or not bcrypt.checkpw(curr.encode('utf-8'), user['password'].encode('utf-8')):
        flash('Incorrect current password', 'error'); return redirect(url_for('settings'))
    if curr == new:
        flash('New password must differ', 'error'); return redirect(url_for('settings'))
    valid, err = validate_password(new)
    if not valid:
        flash(err, 'error'); return redirect(url_for('settings'))
    hashed = bcrypt.hashpw(new.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    if db_manager.users.update_one({'_id': ObjectId(current_user.id)}, {'$set': {'password': hashed}}).modified_count > 0:
        flash('Password updated', 'success'); logout_user(); return redirect(url_for('login'))
    flash('Password update failed', 'error')
    return redirect(url_for('settings'))

def generate_reset_token(email: str) -> Optional[str]:
    user = db_manager.users.find_one({'email': email.lower()})
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    expiration = datetime.now(IST) + timedelta(hours=24)
    db_manager.users.update_one({'_id': user['_id']}, {'$set': {'reset_token': token, 'reset_token_expires': expiration}})
    return token

def validate_reset_token(token: str, new_password: str) -> bool:
    user = db_manager.users.find_one({'reset_token': token, 'reset_token_expires': {'$gt': datetime.now(IST)}})
    if not user:
        return False
    valid, err = validate_password(new_password)
    if not valid:
        return False
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_manager.users.update_one({'_id': user['_id']}, {'$set': {'password': hashed, 'reset_token': None, 'reset_token_expires': None}})
    return True

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """
    Handle password reset request.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('forgot_password.html')
        
        # Generate reset token
        token = generate_reset_token(email)
        if token:
            # Send reset email (implement email sending here)
            flash('Password reset instructions have been sent to your email', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email not found', 'error')
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    if request.method == 'POST':
        new = request.form.get('new_password')
        conf = request.form.get('confirm_password')
        if not new or not conf:
            flash('Enter new password', 'error'); return render_template('reset_password.html', token=token)
        if new != conf:
            flash('Passwords do not match', 'error'); return render_template('reset_password.html', token=token)
        if validate_reset_token(token, new):
            flash('Password reset', 'success'); return redirect(url_for('login'))
        flash('Invalid/expired reset token', 'error'); return redirect(url_for('forgot_password'))
    return render_template('reset_password.html', token=token)

# Chat-related handlers
@socketio.on('connect')
def handle_websocket_connect():
    """Handle WebSocket connection."""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    emit('connected', {'user_id': str(current_user.get_id())})




@socketio.on('get_user_id')
def handle_get_user_id():
    """Get current user's ID."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Not authenticated'})
            return
        emit('user_id', {'user_id': str(current_user.get_id())})
    except Exception as e:
        logger.error(f"Error getting user ID: {e}")
        emit('error', {'message': 'Failed to get user ID'})

@socketio.on('get_conversations')
def handle_get_conversations():
    """Get user's conversations."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
            
        user_id = str(current_user.get_id())
        
        # Get all conversations for user
        conversations = db_manager.get_conversations(user_id)
        
        # Format conversations for frontend
        formatted_conversations = []
        for conv in conversations:
            formatted_conv = {
                'id': str(conv['_id']),
                'title': conv.get('title', 'Conversation'),
                'last_message': conv.get('last_message', 'No messages yet'),
                'updated_at': conv.get('updated_at', datetime.now().isoformat()),
                'message_count': conv.get('message_count', 0)
            }
            formatted_conversations.append(formatted_conv)
            
        # Sort by updated_at in descending order
        formatted_conversations.sort(key=lambda x: x['updated_at'], reverse=True)
        
        emit('conversations_loaded', {
            'conversations': formatted_conversations
        })
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        emit('error', {'message': 'Failed to load conversations'})

@socketio.on('new_conversation')
def handle_new_conversation(data):
    """Create new conversation."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
            
        user_id = str(current_user.get_id())
        
        # Create new conversation
        conversation = db_manager.create_conversation(user_id)
        if not conversation:
            emit('error', {'message': 'Failed to create conversation'})
            return
            
        conversation_id = str(conversation.inserted_id)
        
        # Get conversation details
        conversation_details = db_manager.get_conversations(user_id, conversation_id)
        if not conversation_details:
            emit('error', {'message': 'Failed to get conversation details'})
            return
            
        # Format conversation for frontend
        formatted_conv = {
            'id': conversation_id,
            'title': 'New Conversation',
            'last_message': data.get('content', ''),
            'updated_at': datetime.now().isoformat(),
            'message_count': 0
        }
        
        emit('conversation_created', {
            'conversation': formatted_conv
        })
        
        # If content was provided, process it
        if data.get('content'):
            # Process the message with the conversation ID
            process_chat_message({
                'content': data['content'],
                'type': 'user',
                'timestamp': datetime.now().isoformat(),
                'conversation_id': conversation_id
            })
            
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        emit('error', {'message': 'Failed to create conversation'})

@socketio.on('get_messages')
def handle_get_conversation_messages(data):
    """Get messages for a conversation."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
            
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            emit('error', {'message': 'Conversation ID required'})
            return
            
        messages = db_manager.get_conversation_messages(conversation_id)
        
        # Format messages for frontend
        formatted_messages = []
        for idx, msg in enumerate(messages):
            formatted_msg = {
                'id': str(idx),
                'content': msg.get('content', ''),
                'type': msg.get('type', 'user'),
                'timestamp': msg.get('timestamp', datetime.now().isoformat())
            }
            formatted_messages.append(formatted_msg)
            
        emit('messages_loaded', {
            'conversation_id': conversation_id,
            'messages': formatted_messages
        })
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        emit('error', {'message': 'Failed to get messages'})

@socketio.on('message')
def handle_message(data):
    """Handle incoming chat message."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return

        user_id = str(current_user.get_id())
        content = data.get('content')
        conversation_id = data.get('conversation_id')

        if not content or not conversation_id:
            emit('error', {'message': 'Message content and conversation ID required'})
            return

        timestamp = datetime.now()

        # Get conversation context and process message with LLM once
        context = ContextTracker().get_or_create_context(user_id, conversation_id)
        logger.info(f"Context for conversation {conversation_id}: {context}")
        llm_result = process_message_with_llm(content, user_id, conversation_id, context)
        if not llm_result:
            emit('error', {'message': 'Failed to process message with LLM'})
            return
        logger.info(f"LLM result: {llm_result}")
        ai_response = llm_result.get('response', '')
        ai_intent = llm_result.get('intent')
        ai_entities = llm_result.get('entities', [])
        ai_confidence = llm_result.get('confidence', 0.0)

        # Save user message
        user_metadata = {
            'intent': ai_intent,
            'entities': ai_entities,
            'confidence': ai_confidence
        }
        if not context_tracker.save_chat_message(
            user_id=user_id,
            message=content,
            response=None,
            conversation_id=conversation_id,
            message_type='user',
            timestamp=timestamp,
            metadata=user_metadata
        ):
            emit('error', {'message': 'Failed to save message'})
            return

        emit('message_saved', {
            'message_id': str(ObjectId()),
            'content': content,
            'type': 'user',
            'timestamp': timestamp.isoformat(),
            'conversation_id': conversation_id,
            'metadata': user_metadata
        })

        # Save AI response (no metadata)
        if not context_tracker.save_chat_message(
            user_id=user_id,
            message=None,
            response=ai_response,
            conversation_id=conversation_id,
            message_type='ai',
            timestamp=timestamp
        ):
            emit('error', {'message': 'Failed to save AI response'})
            return

        emit('ai_response', {
            'response_id': str(ObjectId()),
            'content': ai_response,
            'type': 'ai',
            'timestamp': timestamp.isoformat(),
            'conversation_id': conversation_id
        })

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        emit('error', {'message': 'Failed to process message'})

@socketio.on('update_message_metadata')
def handle_update_message_metadata(data):
    """Update message metadata."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
            
        conversation_id = data.get('conversation_id')
        message_index = data.get('message_index')
        metadata = data.get('metadata')
        
        if not all([conversation_id, message_index, metadata]):
            emit('error', {'message': 'Required fields missing'})
            return
            
        if not context_tracker.update_message_metadata(conversation_id, message_index, metadata):
            emit('error', {'message': 'Failed to update metadata'})
            return
            
        emit('metadata_updated', {
            'conversation_id': conversation_id,
            'message_index': message_index,
            'metadata': metadata
        })
    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        emit('error', {'message': 'Failed to update metadata'})

@socketio.on('get_message_metadata')
def handle_get_message_metadata(data):
    """Get message metadata."""
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
            
        conversation_id = data.get('conversation_id')
        message_index = data.get('message_index')
        
        if not all([conversation_id, message_index]):
            emit('error', {'message': 'Required fields missing'})
            return
            
        metadata = context_tracker.get_message_metadata(conversation_id, message_index)
        emit('metadata', {'metadata': metadata})
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        emit('error', {'message': 'Failed to get metadata'})

@socketio.on('delete_conversation')
def handle_delete_conversation(data):
    """Delete conversation directly from database."""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    conversation_id = data.get('conversation_id')
    if not conversation_id:
        emit('error', {'message': 'Conversation ID required'})
        return
    result = db_manager.conversations.delete_one({'_id': ObjectId(conversation_id), 'user_id': str(current_user.get_id())})
    if result.deleted_count == 0:
        emit('error', {'message': 'Failed to delete conversation'})
        return
    emit('conversation_deleted', {'conversation_id': conversation_id})

def handle_parameter_received(data):
    """Store parameter and update prediction with validation using models.py"""
    try:
        prediction_id = data.get('prediction_id')
        parameter_name = data.get('parameter_name')
        parameter_value = data.get('parameter_value')
        
        if not all([prediction_id, parameter_name, parameter_value]):
            emit('error', {'message': 'Missing required fields'})
            return
        # Fetch prediction to get disease type and current parameters
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction:
            emit('error', {'message': 'Prediction not found'})
            return
        disease_type = prediction.get('disease_type', '').lower()
        parameters = prediction.get('parameters', {})
        # Validate parameter using centralized validation
        parameters[parameter_name] = parameter_value
        is_valid, errors = validate_all_parameters(disease_type, parameters)
        if not is_valid:
            emit('error', {'message': errors.get(parameter_name) or next(iter(errors.values()))})
            return
        # Update parameter in database
        db_manager.predictions.update_one(
            {'_id': ObjectId(prediction_id)},
            {'$set': {
                f'parameters.{parameter_name}': parameter_value,
                'updated_at': datetime.now(IST)
            }}
        )
        emit('parameter_updated', {
            'prediction_id': prediction_id,
            'parameter_name': parameter_name,
            'parameter_value': parameter_value
        })
    except Exception as e:
        logger.error(f"Error updating parameter: {e}")
        emit('error', {'message': f'Error updating parameter: {str(e)}'})

@socketio.on('predict')
@login_required
def handle_predict(data):
    """Handle predict action using model.py logic"""
    try:
        prediction_id = data.get('prediction_id')
        if not prediction_id:
            emit('error', {'message': 'Missing required fields'})
            return
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction:
            emit('error', {'message': 'Prediction not found'})
            return
        disease_type = prediction.get('disease_type', '').lower()
        parameters = prediction.get('parameters', {})
        predictor = get_predictor(disease_type)
        if not predictor:
            emit('error', {'message': f'No predictor found for {disease_type}'})
            return
        # Validate all parameters before prediction
        is_valid, errors = validate_all_parameters(disease_type, parameters)
        if not is_valid:
            emit('error', {'message': next(iter(errors.values()))})
            return
        # Run prediction
        try:
            prediction_result, confidence = predictor.predict(parameters)
            result = {
                'prediction': prediction_result,
                'confidence': confidence
            }
        except Exception as e:
            emit('error', {'message': f'Error during prediction: {str(e)}'})
            return
        # Update prediction record
        db_manager.predictions.update_one(
            {'_id': ObjectId(prediction_id)},
            {'$set': {
                'result': result,
                'status': 'completed',
                'completed_at': datetime.now(IST)
            }}
        )
        emit('prediction_completed', {
            'prediction_id': prediction_id,
            'result': result,
            'status': 'completed'
        })
    except Exception as e:
        logger.error(f"Error handling prediction result: {e}")
        emit('error', {'message': f'Error handling prediction result: {str(e)}'})



@app.route('/api/predictions')
@login_required
def get_predictions():
    """
    Get user's predictions with filtering options.
    
    Returns:
        JSON response with predictions
    """
    try:
        # Get query parameters
        disease_type = request.args.get('disease_type', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Build query
        query = {'user_id': str(current_user.id)}
        
        if disease_type:
            query['disease_type'] = disease_type
        
        if start_date and end_date:
            try:
                query['created_at'] = {
                    '$gte': datetime.strptime(start_date, '%Y-%m-%d'),
                    '$lte': datetime.strptime(end_date, '%Y-%m-%d')
                }
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid date format'
                }), 400
        
        # Get predictions
        predictions = db_manager.get_user_predictions(str(current_user.id))
        
        return jsonify({
            'status': 'success',
            'predictions': predictions
        })
        
    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/prediction/<prediction_id>')
@login_required
def get_prediction(prediction_id):
    """
    Get detailed prediction information.
    
    Args:
        prediction_id: ID of the prediction
        
    Returns:
        JSON response with prediction details
    """
    try:
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction or prediction['user_id'] != str(current_user.id):
            return jsonify({
                'status': 'error',
                'message': 'Prediction not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'prediction': prediction
        })
        
    except Exception as e:
        logger.error(f"Error fetching prediction: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/prediction/<prediction_id>/delete', methods=['DELETE'])
@login_required
def delete_prediction(prediction_id):
    """
    Delete a prediction.
    
    Args:
        prediction_id: ID of the prediction to delete
        
    Returns:
        JSON response with deletion status
    """
    try:
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction or prediction['user_id'] != str(current_user.id):
            return jsonify({
                'status': 'error',
                'message': 'Prediction not found'
            }), 404
            
        if not db_manager.delete_prediction(prediction_id):
            return jsonify({
                'status': 'error',
                'message': 'Failed to delete prediction'
            }), 500
            
        # Emit delete event to all connected clients
        socketio.emit('prediction_deleted', {
            'prediction_id': str(prediction_id)  # Convert ObjectId to string
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Prediction deleted successfully'
        })
        # Emit flash message
        emit('flash_message', {'message': 'Prediction deleted successfully.', 'category': 'success'})
    except Exception as e:
        logger.error(f"Error deleting prediction: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@socketio.on('new_prediction')
@login_required
def handle_new_prediction(data):
    """Handle new prediction creation"""
    try:
        disease = data.get('disease')
        if not disease:
            emit('error', {'message': 'Disease type is required'})
            return
            
        # Create new prediction
        prediction_id = db_manager.save_prediction(
            str(current_user.id),
            disease,
            {}
        )
        
        if not prediction_id:
            emit('error', {'message': 'Failed to create prediction'})
            return
            
        # Broadcast new prediction to all connected clients
        socketio.emit('prediction_created', {
            'prediction_id': str(prediction_id),  # Convert ObjectId to string
            'disease': disease,
            'created_at': datetime.now(IST).isoformat()
        })
        
    except Exception as e:
        logger.error(f"New prediction error: {e}")
        emit('error', {'message': str(e)})

@socketio.on('update_prediction')
@login_required
def handle_update_prediction(data):
    """Handle prediction parameter updates with LLM-powered follow-up and recommendations"""
    try:
        prediction_id = data.get('prediction_id')
        parameters = data.get('parameters', {})
        conversation_id = data.get('conversation_id')
        
        if not prediction_id or not parameters:
            emit('error', {'message': 'Invalid update data'})
            return

        # Fetch current prediction and context
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction:
            emit('error', {'message': 'Prediction not found'})
            return
        user_id = prediction.get('user_id')
        
        # Get conversation context if available
        context = ContextTracker().get_or_create_context(user_id, conversation_id) if conversation_id else {}
        # Validate parameters before proceeding
        is_valid, validation_errors = validate_parameters(prediction.get('disease_type', ''), parameters)
        if not is_valid:
            emit('error', {'message': 'Parameter validation failed', 'errors': validation_errors})
            return

        # Use LLM to generate follow-ups and recommendations based on updated parameters
        llm_result = process_message_with_llm(
            message=f"Update prediction parameters: {parameters}",
            user_id=user_id,
            conversation_id=conversation_id,
            context=context
        )
        follow_up_questions = llm_result.get('follow_up_questions', []) if llm_result else []
        recommendations = llm_result.get('recommendations', []) if llm_result else []
        # Update prediction
        result = prediction.get('result') if prediction else None
        update_data = {
            'parameters': parameters,
            'updated_at': datetime.now(IST),
            'follow_up_questions': follow_up_questions,
            'recommendations': recommendations,
            'result': result
        }
        if not db_manager.update_prediction(prediction_id, update_data):
            emit('error', {'message': 'Failed to update prediction'})
            return
    except Exception as e:
        logger.error(f"Update prediction error: {e}")
        emit('error', {'message': str(e)})

@app.route('/api/prediction/<prediction_id>')
@login_required
def get_prediction_details(prediction_id):
    """
    Get detailed prediction information.
    
    Args:
        prediction_id: ID of the prediction
        
    Returns:
        Plain text response with prediction details
    """
    try:
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction:
            return "Error: Prediction not found", 404
            
        # Format the response
        response = f"""
Prediction ID: {prediction['id']}
Disease Type: {prediction['disease_type']}
Confidence: {prediction['confidence']}
Prediction: {prediction['prediction']}
Created At: {prediction['created_at'].strftime('%Y-%m-%d %H:%M')}
Parameters: {prediction.get('parameters', {})}
Follow-up Questions: {prediction.get('follow_up_questions', [])}
Recommendations: {prediction.get('recommendations', [])}
"""
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching prediction details: {e}")
        return f"Error: {str(e)}", 500

@socketio.on('prediction_created')
@login_required
def handle_prediction_created(data):
    """Handle new prediction creation"""
    try:
        prediction_id = data.get('prediction_id')
        disease = data.get('disease')
        
        if not prediction_id or not disease:
            emit('error', {'message': 'Invalid prediction data'})
            return

        # Get prediction details
        prediction = db_manager.get_prediction(prediction_id)
        if not prediction:
            emit('error', {'message': 'Prediction not found'})
            return

        # Calculate updated metrics
        metrics = {
            'prediction_trends': get_prediction_trends(current_user.id, db_manager),
            'most_predicted': get_most_predicted_conditions(current_user.id, db_manager),
            'accuracy': calculate_prediction_accuracy(current_user.id, db_manager)
        }

        # Broadcast updates to all connected clients
        socketio.emit('dashboard_metrics_updated', {
            'prediction_id': prediction_id,
            'status': 'created',
            'metrics': metrics,
            'message': f"Metrics updated for prediction {prediction_id}"
        })

    except Exception as e:
        logger.error(f"Error handling prediction creation: {e}")
        emit('error', {'message': f'Error handling prediction creation: {str(e)}'})

@socketio.on('prediction_updated')
@login_required
def handle_prediction_updated(data):
    """Handle prediction update"""
    try:
        prediction_id = data.get('prediction_id')
        update_data = data.get('update_data', {})
        
        if not prediction_id or not update_data:
            emit('error', {'message': 'Invalid update data'})
            return

        # Update prediction
        if not db_manager.update_prediction(prediction_id, update_data):
            emit('error', {'message': 'Failed to update prediction'})
            return

        # Calculate updated metrics
        metrics = {
            'prediction_trends': get_prediction_trends(current_user.id, db_manager),
            'most_predicted': get_most_predicted_conditions(current_user.id, db_manager),
            'accuracy': calculate_prediction_accuracy(current_user.id, db_manager)
        }

        # Get updated prediction
        prediction = db_manager.get_prediction(prediction_id)

        # Broadcast updates to all connected clients
        socketio.emit('prediction_updated', {
            'prediction_id': prediction_id,
            'status': 'updated',
            'message': f"Prediction {prediction_id} updated successfully",
            'prediction': prediction,
            'metrics': metrics
        })

    except Exception as e:
        logger.error(f"Error handling prediction update: {e}")
        emit('error', {'message': f'Error handling prediction update: {str(e)}'})

@socketio.on('prediction_deleted')
@login_required
def handle_prediction_deleted(data):
    """Handle prediction deletion"""
    try:
        prediction_id = data.get('prediction_id')
        
        if not prediction_id:
            emit('error', {'message': 'Invalid prediction ID'})
            return
            
        # Delete prediction
        if not db_manager.delete_prediction(prediction_id):
            emit('error', {'message': 'Failed to delete prediction'})
            return
            
        # Calculate updated metrics
        metrics = {
            'prediction_trends': get_prediction_trends(current_user.id, db_manager),
            'most_predicted': get_most_predicted_conditions(current_user.id, db_manager),
            'accuracy': calculate_prediction_accuracy(current_user.id, db_manager)
        }
        
        # Broadcast updates to all connected clients
        socketio.emit('dashboard_metrics_updated', {
            'metrics': metrics,
            'deleted_prediction_id': str(prediction_id)  # Convert ObjectId to string
        })
        # Emit flash message
        emit('flash_message', {'message': 'Prediction deleted successfully.', 'category': 'success'})
    except Exception as e:
        logger.error(f"Error handling prediction deletion: {e}")
        emit('error', {'message': str(e)})

@socketio.on('connect')
@login_required
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    try:
        if current_user.is_authenticated:
            # Send initial metrics
            metrics = {
                'prediction_trends': get_prediction_trends(current_user.id, db_manager),
                'most_predicted': get_most_predicted_conditions(current_user.id, db_manager),
                'accuracy': calculate_prediction_accuracy(current_user.id, db_manager)
            }
            emit('dashboard_metrics_updated', {'metrics': metrics})
        else:
            emit('error', {'message': 'Not authenticated'})
    except Exception as e:
        logger.error(f"Error in connect handler: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_metrics')
@login_required
def handle_get_metrics():
    try:
        metrics = {
            'prediction_trends': get_prediction_trends(current_user.id, db_manager),
            'most_predicted': get_most_predicted_conditions(current_user.id, db_manager),
            'accuracy': calculate_prediction_accuracy(current_user.id, db_manager)
        }
        emit('dashboard_metrics_updated', {'metrics': metrics})
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        emit('error', {'message': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


if __name__ == '__main__':
    try:
        # Start Flask application with SocketIO
        socketio.run(
            app,
            debug=True,
            host='0.0.0.0',
            port=5000,
            allow_unsafe_werkzeug=True
        )
    
    except Exception as e:
        logger.critical(f"Application startup error: {e}")
        raise
