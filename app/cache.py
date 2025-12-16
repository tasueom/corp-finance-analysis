"""
기업 코드 캐시 관리 모듈
Flask 앱 시작 시 백그라운드에서 기업 코드 목록을 로드합니다.
"""
import threading
from app.api_service import load_corp_code_cache


def init_cache():
    """
    Flask 앱 시작 시 기업 코드 캐시를 백그라운드에서 로드합니다.
    이 함수는 create_app()에서 호출됩니다.
    """
    def load_cache_background():
        """백그라운드 스레드에서 캐시 로드"""
        load_corp_code_cache()
    
    # 백그라운드 스레드 시작 (데몬 스레드로 설정하여 메인 프로세스 종료 시 함께 종료)
    cache_thread = threading.Thread(target=load_cache_background, daemon=True)
    cache_thread.start()

