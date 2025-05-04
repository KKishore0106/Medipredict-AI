import logging
import os
import json
import groq
from dotenv import load_dotenv
from system_prompts import SYSTEM_PROMPTS

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self):
        try:
            api_key = os.environ.get('GROQ_API_KEY')
            if not api_key:
                logger.error('GROQ_API_KEY not found in environment variables.')
                self.client = None
            else:
                self.client = groq.Client(api_key=api_key)
        except Exception as e:
            logger.error(f'Error initializing Groq client: {e}')
            self.client = None

    def process_message(self, input_data):
        if not self.client:
            return {
                'intent': None,
                'entities': [],
                'confidence': 0.0,
                'response': "AI service unavailable."
            }
        try:
            model = 'llama3-70b-8192'
            temperature = 0.5
            user_message = input_data.get("message", "")
            conversation_messages = input_data.get("messages", [])

            # Start with the system prompt
            messages = [{"role": "system", "content": SYSTEM_PROMPTS.strip()}]

            # Add previous messages (context)
            for msg in conversation_messages:
                # Ensure each message has the required role property
                role = 'user' if msg.get('type') == 'user' else 'assistant'
                messages.append({
                    'role': role,
                    'content': msg.get('content', '')
                })

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Call Groq
            groq_response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=512
            )

            response_text = groq_response.choices[0].message.content.strip()
            try:
                return json.loads(response_text)
            except Exception as e:
                raise Exception(f"LLM did not return valid JSON: {e}")
        except Exception as e:
            logger.error(f'Groq API error: {e}')
            return {
                'intent': None,
                'entities': [],
                'confidence': 0.0,
                'response': "AI service error."
            }

# Global processor instance
llm_processor = LLMProcessor()

def process_message_with_llm(message, user_id, conversation_id, context):
    try:
        input_data = {
            'message': message,
            'user_id': user_id,
            'conversation_id': conversation_id,
            'messages': context.get('messages', [])
        }
        result = llm_processor.process_message(input_data)
        return {
            'intent': result.get('intent'),
            'entities': result.get('entities', []),
            'confidence': result.get('confidence', 0.0),
            'response': result.get('response')
        }
    except Exception as e:
        logger.error(f"Error processing message with LLM: {e}")
        return None
