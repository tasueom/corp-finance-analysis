"""
유틸리티 함수 모듈
"""
import os, uuid, requests

# GA4 서버 이벤트 전송 설정
MEASUREMENT_ID = os.getenv('MEASUREMENT_ID') # GA4 측정 ID
API_SECRET = os.getenv('API_SECRET') # Measurement Protocol용 비밀키
CLIENT_ID = str(uuid.uuid4()) # 사용자를 구분하기 위한 임의의 사용자 ID

def send_event_to_ga4(event_name, params):
    """
    GA4 서버로 이벤트 데이터를 전송하는 함수

    :param event_name: GA4에서 확인할 이벤트 이름
    :param params: 이벤트와 함께 전송할 추가 정보 (딕셔너리 형태)
    """

    # GA4 이벤트 전송용 URL
    url = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"

    # GA4에 전달할 데이터 구조
    payload = {
        "client_id": CLIENT_ID,       # 사용자 식별 ID
        "events": [
            {
                "name": event_name,   # 이벤트 이름
                "params": params      # 이벤트 상세 데이터
            }
        ]
    }
    
    # 실제 HTTP POST 요청을 보내 GA 서버로 전송
    # 이 과정에서 웹페이지 작동에는 영향을 주지 않습니다.
    requests.post(url, json=payload)


def read_readme():
    """
    README.md 파일을 읽어서 내용을 반환합니다.
    
    Returns:
        str: README.md 파일 내용
    """
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "README.md 파일을 찾을 수 없습니다."
    except Exception as e:
        return f"README.md 파일을 읽는 중 오류가 발생했습니다: {str(e)}"


def format_korean_number(num):
    """
    숫자를 조 / 억 단위로 변환하여 문자열로 반환
    None 또는 0은 '-' 로 표시
    """
    if num is None:
        return "-"

    try:
        num = float(num)
    except:
        return "-"

    if num == 0:
        return "-"

    abs_num = abs(num)

    if abs_num >= 1_0000_0000_0000:  # 1조
        formatted = f"{num / 1_0000_0000_0000:.1f}조"
    elif abs_num >= 1_0000_0000:  # 1억
        formatted = f"{num / 1_0000_0000:.1f}억"
    else:
        formatted = f"{num:,.0f}"

    return formatted


def validate_year(year_str, min_year=None):
    """
    연도 유효성 검사
    
    Args:
        year_str: 검사할 연도 문자열
        min_year: 최소 연도 (None이면 검사 안함)
    
    Returns:
        tuple: (is_valid: bool, year_int: int or None, error_message: str or None)
    """
    if not year_str:
        return False, None, "연도를 입력해주세요."
    
    try:
        year_int = int(year_str)
        if min_year and year_int < min_year:
            return False, None, f"연도는 {min_year}년 이상이어야 합니다."
        return True, year_int, None
    except ValueError:
        return False, None, "올바른 연도를 입력해주세요."


def get_latest_year_from_years(years):
    """
    연도 리스트에서 최근 연도를 반환
    
    Args:
        years: 연도 리스트 [(year,), ...]
    
    Returns:
        str: 최근 연도 문자열, 없으면 None
    """
    if years:
        return str(years[0][0])
    return None


def check_duplicate_compare_items(compare_list):
    """
    비교 리스트에서 중복 항목 체크
    
    Args:
        compare_list: 비교 리스트 [{"corp": "...", "year": "..."}, ...]
    
    Returns:
        tuple: (unique_list: list, duplicates: list)
    """
    seen = set()
    duplicates = []
    
    for item in compare_list:
        key = (item["corp"], item["year"])
        if key in seen:
            duplicates.append(f"{item['corp']}({item['year']})")
        else:
            seen.add(key)
    
    unique_list = [{"corp": corp, "year": year} for corp, year in seen]
    return unique_list, duplicates

