from flask import Flask, session
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

def create_app():
    """Flask 애플리케이션 팩토리 함수"""
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30분 (초 단위)
    
    # 라우트 등록
    from app import routes
    
    # 기업 코드 캐시 초기화 (백그라운드에서 로드)
    from app.cache import init_cache
    init_cache()
    
    return app