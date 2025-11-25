from flask import Flask, session
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

def create_app():
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30분 (초 단위)
    
    from app import routes
    
    return app