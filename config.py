import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Database configuration
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME', 'medi_predict')
    
    # Groq configuration
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    
    # Other configuration
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    PORT = int(os.environ.get('PORT', '5000'))
