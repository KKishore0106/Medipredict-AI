from datetime import datetime, timedelta
from pytz import timezone
import logging
import threading

IST = timezone('Asia/Kolkata')
logger = logging.getLogger(__name__)

class ContextTracker:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ContextTracker, cls).__new__(cls)
                cls._instance.db_manager = None
        return cls._instance

    def __init__(self):
        pass

    @classmethod
    def initialize(cls, db_manager):
        """Initialize with database manager"""
        if cls._instance is None:
            cls._instance = cls()
        cls._instance.db_manager = db_manager
        return cls._instance

    def _handle_error(self, func_name, e):
        logger.error(f"Error in {func_name}: {e}")
        raise

    def save_chat_message(
        self, user_id, message, response, context=None, conversation_id=None,
        timestamp=None, message_type='user', status='completed',
        intent=None, entities=None, confidence=None, metadata=None
    ):
        """Save a chat message with proper context tracking, supporting custom metadata."""
        try:
            if self.db_manager.conversations is None:
                raise Exception("Conversations collection not initialized")
            
            # Timestamp
            timestamp = (timestamp or datetime.now(IST)).isoformat() \
                if not isinstance(timestamp, str) else timestamp
    
            # Content
            content = message if message_type == 'user' else response
    
            # Metadata (only for user messages)
            message_metadata = None
            if message_type == 'user':
                message_metadata = metadata or {
                    'intent': intent,
                    'entities': entities or [],
                    'confidence': confidence or 0.0
                }
    
            # Build message_data
            message_data = {
                'content': content,
                'type': message_type,
                'timestamp': timestamp,
                'status': status
            }
            if message_metadata:
                message_data['metadata'] = message_metadata
    
            # Save to database
            if not self.db_manager.add_message_to_conversation(conversation_id, message_data):
                raise Exception("Failed to save message to database")
            return True
    
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            return False

    def get_conversation_details(self, user_id, conversation_id, include_messages=False):
        """Get conversation details"""
        try:
            conversation = self.db_manager.get_conversations(user_id, conversation_id)
            if not conversation:
                return None
                
            result = {
                'id': str(conversation['_id']),
                'title': conversation.get('title'),
                'created_at': conversation.get('created_at'),
                'last_message_at': conversation.get('last_message_at'),
                'message_count': conversation.get('message_count', 0),
                'status': conversation.get('status')
            }
            
            if include_messages:
                result['messages'] = self.get_conversation_messages(conversation_id)
                
            return result
        except Exception as e:
            self._handle_error('get_conversation_details', e)

    def get_user_conversations(self, user_id):
        """Get user's conversations"""
        try:
            return [{
                'id': str(conv['_id']),
                'title': conv.get('title'),
                'created_at': conv.get('created_at'),
                'last_message_at': conv.get('last_message_at'),
                'message_count': conv.get('message_count', 0),
                'status': conv.get('status')
            } for conv in self.db_manager.get_conversations(user_id)]
        except Exception as e:
            self._handle_error('get_user_conversations', e)

    def get_disease_context(self, user_id, conversation_id=None):
        """Get disease prediction context"""
        try:
            query = {'user_id': user_id}
            if conversation_id:
                query['conversation_id'] = conversation_id
                
            prediction = self.db_manager.predictions.find_one(
                query,
                sort=[('timestamp', -1)]
            )
            
            return {
                'disease': prediction.get('disease_type'),
                'status': prediction.get('status'),
                'timestamp': prediction.get('timestamp')
            } if prediction else None
        except Exception as e:
            self._handle_error('get_disease_context', e)

    def get_user_history(self, user_id):
        """Get user's conversation history"""
        try:
            conversations = self.db_manager.conversations.find(
                {'user_id': user_id},
                sort=[('created_at', 1)]
            )
            
            return "\n".join([
                f"Conversation {conv['_id']} - Created: {conv['created_at'].isoformat()}"
                f" - Messages: {conv.get('message_count', 0)}"
                for conv in conversations
            ])
        except Exception as e:
            self._handle_error('get_user_history', e)

    def get_or_create_context(self, user_id, conversation_id=None, limit=10):
        """Get or create conversation context, limiting to last N messages by default."""
        try:
            if not conversation_id:
                conversation = self.db_manager.create_conversation(user_id)
                if not conversation:
                    return None
                conversation_id = str(conversation['_id'])
            return self.get_context(user_id, conversation_id, limit=limit)
        except Exception as e:
            self._handle_error('get_or_create_context', e)

    def get_context(self, user_id, conversation_id, limit=10):
        """Return conversation context for LLM and chat processing, limited to last N messages."""
        try:
            messages = self.get_conversation_messages(conversation_id)
            if limit is not None and len(messages) > limit:
                messages = messages[-limit:]
            return {
                'messages': messages,
                'conversation_id': conversation_id,
                'user_id': user_id
            }
        except Exception as e:
            self._handle_error('get_context', e)
            return {'messages': [], 'conversation_id': conversation_id, 'user_id': user_id}


    def create_context(self, user_id, conversation_id=None):
        """Create new conversation context"""
        try:
            if not conversation_id:
                conversation = self.db_manager.create_conversation(user_id)
                if not conversation:
                    return None
                conversation_id = str(conversation['_id'])
                
            return self.get_context(user_id, conversation_id)
        except Exception as e:
            self._handle_error('create_context', e)

    def get_conversation_messages(self, conversation_id):
        """Get messages for a conversation."""
        try:
            if self.db_manager.conversations is None:
                raise Exception("Conversations collection not initialized")
                
            messages = self.db_manager.get_conversation_messages(conversation_id)
            if not messages:
                return []
                
            # Convert datetime objects to ISO format
            for message in messages:
                if 'timestamp' in message and isinstance(message['timestamp'], datetime):
                    message['timestamp'] = message['timestamp'].isoformat()
                    
            return messages
        except Exception as e:
            self._handle_error('get_conversation_messages', e)
            return []