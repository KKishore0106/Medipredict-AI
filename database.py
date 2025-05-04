"""Database operations for MediPredict application."""

import os
import logging
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.predictions = None
        self.conversations = None

    def initialize_db(self):
        """Initialize database connection."""
        try:
            # Get connection string from environment
            mongo_uri = os.environ.get('MONGODB_URI')
            if not mongo_uri:
                logger.error('MONGODB_URI not found in environment variables.')
                return False
                
            # Get database name from environment
            db_name = os.environ.get('MONGODB_DB_NAME', 'medi_predict')
            
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[db_name]
            
            # Initialize collections
            self.users = self.db.get_collection('users')
            self.predictions = self.db.get_collection('predictions')
            self.conversations = self.db.get_collection('conversations')
            
            # Create indexes
            self.conversations.create_index([('user_id', 1)])
            self.conversations.create_index([('updated_at', -1)])
            
            return True
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def get_user(self, user_id):
        """Get user by ID."""
        try:
            return self.users.find_one({'_id': ObjectId(user_id)})
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user(self, user_id, update_data):
        """Update user document."""
        try:
            result = self.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False

    def add_message_to_conversation(self, conversation_id, message_data):
        """Add message to conversation. Supports modular backend-driven workflows."""
        try:
            content = message_data.get('content', message_data.get('message', message_data.get('response', '')))
            timestamp = message_data.get('timestamp', datetime.now())
            # Convert datetime to ISO format if needed
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            message = {
                'content': content,
                'type': message_data['type'],
                'timestamp': timestamp,
                'status': message_data.get('status', 'completed'),
                'metadata': message_data.get('metadata', {})
            }
            # Robustly update conversation document with new message and updated context
            result = self.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {
                    '$push': {'messages': message},
                    '$inc': {'message_count': 1},
                    '$set': {
                        'updated_at': timestamp,
                        'last_message_at': timestamp,
                        'last_message': content
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False

    def get_conversation_messages(self, conversation_id):
        """Get conversation messages."""
        try:
            conversation = self.conversations.find_one(
                {'_id': ObjectId(conversation_id)},
                {'messages': 1}
            )
            return conversation.get('messages', []) if conversation else []
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    def update_message_metadata(self, conversation_id, message_index, metadata):
        """Update message metadata."""
        try:
            result = self.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {
                    '$set': {
                        f'messages.{message_index}.metadata': metadata,
                        'updated_at': datetime.now().isoformat()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            return False

    def get_message_metadata(self, conversation_id, message_index):
        """Get message metadata."""
        try:
            conversation = self.conversations.find_one(
                {'_id': ObjectId(conversation_id)},
                {'messages': {'$slice': [message_index, 1]}}
            )
            if not conversation or not conversation['messages']:
                return None
                
            message = conversation['messages'][0]
            return message.get('metadata', {}) if message.get('type') == 'user' else None
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return None

    def create_conversation(self, user_id):
        """Create new conversation."""
        try:
            return self.conversations.insert_one({
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'message_count': 0,
                'status': 'active'
            })
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return None

    def get_conversations(self, user_id, conversation_id=None):
        """Get conversations for user."""
        try:
            query = {'user_id': user_id}
            if conversation_id:
                query['_id'] = ObjectId(conversation_id)
                
            conversations = list(self.conversations.find(query))
            
            # Convert datetime objects to ISO format strings
            for conv in conversations:
                if 'created_at' in conv and isinstance(conv['created_at'], datetime):
                    conv['created_at'] = conv['created_at'].isoformat()
                if 'updated_at' in conv and isinstance(conv['updated_at'], datetime):
                    conv['updated_at'] = conv['updated_at'].isoformat()
                if 'last_message_at' in conv and isinstance(conv['last_message_at'], datetime):
                    conv['last_message_at'] = conv['last_message_at'].isoformat()
                
                # Convert message timestamps if they exist
                if 'messages' in conv:
                    for message in conv['messages']:
                        if 'timestamp' in message and isinstance(message['timestamp'], datetime):
                            message['timestamp'] = message['timestamp'].isoformat()
            
            return conversations
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []

    def delete_conversation(self, conversation_id):
        """Delete conversation."""
        try:
            return self.conversations.delete_one({'_id': ObjectId(conversation_id)}).deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False

    def update_conversation_status(self, conversation_id, status):
        """Update conversation status."""
        try:
            return self.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$set': {'status': status, 'updated_at': datetime.now().isoformat()}}
            ).modified_count > 0
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False


    def delete_prediction(self, prediction_id):
        """
        Delete a prediction by its ID.
        Args:
            prediction_id: str
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.predictions.delete_one({'_id': ObjectId(prediction_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting prediction: {e}")
            return False

    def update_prediction(self, prediction_id, update_data):
        """Update prediction."""
        try:
            return self.predictions.update_one(
                {'_id': ObjectId(prediction_id)},
                {'$set': update_data}
            ).modified_count > 0
        except Exception as e:
            logger.error(f"Error updating prediction: {e}")
            return False

    def get_prediction(self, prediction_id):
        """Get prediction by ID."""
        try:
            prediction = self.predictions.find_one({'_id': ObjectId(prediction_id)})
            if prediction and 'created_at' in prediction and isinstance(prediction['created_at'], datetime):
                prediction['created_at'] = prediction['created_at'].isoformat()
            if prediction and 'updated_at' in prediction and isinstance(prediction['updated_at'], datetime):
                prediction['updated_at'] = prediction['updated_at'].isoformat()
            return prediction
        except Exception as e:
            logger.error(f"Error getting prediction: {e}")
            return None
    
    
    def get_user_predictions(self, user_id):
        """Get user predictions."""
        try:
            predictions = list(self.predictions.find(
                {'user_id': user_id},
                sort=[('created_at', -1)]
            ))
            for prediction in predictions:
                if 'created_at' in prediction and isinstance(prediction['created_at'], datetime):
                    prediction['created_at'] = prediction['created_at'].isoformat()
                if 'updated_at' in prediction and isinstance(prediction['updated_at'], datetime):
                    prediction['updated_at'] = prediction['updated_at'].isoformat()
            return predictions
        except Exception as e:
            logger.error(f"Error getting user predictions: {e}")
            return []
# Create global instance
db_manager = DatabaseManager()

def init_database():
    """Initialize the database."""
    return db_manager.initialize_db()