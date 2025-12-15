import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import os
import pandas as pd
import math
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from app import db
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
import numpy as np

# .env 파일 로드 (명시적으로 경로 지정 및 여러 경로 시도)
base_dir = Path(__file__).parent.parent
env_paths = [
    base_dir / '.env',
    Path.cwd() / '.env',
    Path('.env')
]

# 여러 경로에서 .env 파일 찾아서 로드
env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        env_loaded = True
        break

# 경로를 지정하지 않고도 한 번 더 시도 (현재 작업 디렉토리 기준)
if not env_loaded:
    load_dotenv(override=True)

# 환경변수 로드 (공백 제거)
API_KEY = os.environ.get('API_KEY', '').strip()
BASE_URL = os.environ.get('BASE_URL', 'https://opendart.fss.or.kr/api').strip()

def get_corp_code(corp_name):
    """
    기업 이름으로 DART 기업 코드를 조회합니다.
    
    Args:
        corp_name (str): 검색할 기업 이름
        
    Returns:
        str: 기업 코드 (corp_code), 찾지 못한 경우 None
    """
    if not API_KEY:
        # 환경변수 확인을 위한 디버깅 정보
        env_keys = [k for k in os.environ.keys() if 'API' in k.upper() or 'KEY' in k.upper()]
        raise ValueError(
            f"API_KEY 환경변수가 설정되지 않았습니다. "
            f"현재 환경변수 중 API/KEY 관련: {env_keys if env_keys else '없음'}"
        )
    
    # corpCode.xml 다운로드 URL
    url = f'{BASE_URL}/corpCode.xml?crtfc_key={API_KEY}'
    
    # 디버깅: API_KEY가 실제로 설정되었는지 확인 (키의 일부만 표시)
    if len(API_KEY) < 10:
        raise ValueError(f"API_KEY가 너무 짧습니다. 올바른 키인지 확인해주세요. (길이: {len(API_KEY)})")
    
    try:
        # ZIP 파일로 압축된 XML 다운로드
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 응답 내용 확인 (에러 메시지인지 체크)
        content_type = response.headers.get('Content-Type', '').lower()
        response_text = response.text[:200].lower() if hasattr(response, 'text') else ''
        
        # HTML 응답인지 확인 (인증 실패 또는 잘못된 API 키)
        if 'text/html' in content_type or response_text.startswith('<!doctype html') or response_text.startswith('<html'):
            # API_KEY 디버깅 정보 (키의 앞 4자만 표시)
            key_preview = API_KEY[:4] + '...' if API_KEY and len(API_KEY) > 4 else 'None'
            raise Exception(
                f"DART API 인증 실패: API_KEY가 올바르지 않거나 설정되지 않았습니다.\n"
                f"현재 API_KEY (앞 4자): {key_preview}\n"
                f"API_KEY 길이: {len(API_KEY) if API_KEY else 0}\n"
                f"호출 URL: {url.split('?')[0]}?crtfc_key=***\n"
                f".env 파일 위치를 확인하고 올바른 API_KEY를 설정해주세요.\n"
                f"(DART Open API 홈페이지: https://opendart.fss.or.kr/)"
            )
        
        # JSON 에러 응답인지 확인
        if 'application/json' in content_type or response.content[:1] == b'{':
            try:
                error_data = response.json()
                error_message = error_data.get('message', '알 수 없는 오류')
                status = error_data.get('status', '')
                raise Exception(f"DART API 오류 (상태: {status}): {error_message}")
            except ValueError:
                pass  # JSON 파싱 실패 시 계속 진행
        
        # ZIP 파일인지 확인
        if not response.content.startswith(b'PK'):
            # ZIP 파일 시그니처가 아닌 경우
            raise Exception(
                "다운로드한 파일이 ZIP 형식이 아닙니다. "
                "API_KEY가 올바르게 설정되어 있는지 확인해주세요. "
                f"(응답 상태 코드: {response.status_code}, Content-Type: {content_type})"
            )
        
        # ZIP 파일 압축 해제 및 XML 파싱
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # 파일 목록 확인
                file_list = z.namelist()
                
                # CORPCODE.xml 파일 찾기 (대소문자 구분 없이)
                xml_file = None
                for fname in file_list:
                    if fname.upper() == 'CORPCODE.XML':
                        xml_file = fname
                        break
                
                if not xml_file:
                    raise Exception(f"ZIP 파일에 CORPCODE.xml이 없습니다. 파일 목록: {file_list}")
                
                # CORPCODE.xml 파일 열기
                with z.open(xml_file) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    
                    # 기업 이름으로 검색
                    for child in root:
                        corp_name_elem = child.find('corp_name')
                        if corp_name_elem is not None and corp_name_elem.text == corp_name:
                            corp_code_elem = child.find('corp_code')
                            if corp_code_elem is not None:
                                return corp_code_elem.text
        except zipfile.BadZipFile as e:
            error_text = response.text[:500] if hasattr(response, 'text') else str(response.content[:500])
            raise Exception(f"다운로드한 파일이 올바른 ZIP 형식이 아닙니다. 응답 내용: {error_text}")
        
        return None
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"기업 코드 조회 중 네트워크 오류 발생: {str(e)}")
    except ET.ParseError as e:
        raise Exception(f"XML 파싱 중 오류 발생: {str(e)}")

def search_corps(search_term, limit=50):
    """
    검색어가 포함된 기업 목록을 조회합니다.
    
    Args:
        search_term (str): 검색할 기업 이름 (부분 일치)
        limit (int): 최대 반환 개수 (기본값: 50)
        
    Returns:
        list: 기업 정보 리스트 [{'corp_name': '기업명', 'corp_code': '기업코드'}, ...]
    """
    if not API_KEY:
        raise ValueError("API_KEY 환경변수가 설정되지 않았습니다.")
    
    if not search_term or len(search_term.strip()) < 1:
        return []
    
    search_term = search_term.strip()
    
    # corpCode.xml 다운로드 URL
    url = f'{BASE_URL}/corpCode.xml?crtfc_key={API_KEY}'
    
    try:
        # ZIP 파일로 압축된 XML 다운로드
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 응답 내용 확인 (에러 메시지인지 체크)
        content_type = response.headers.get('Content-Type', '').lower()
        response_text = response.text[:200].lower() if hasattr(response, 'text') else ''
        
        # HTML 응답인지 확인 (인증 실패 또는 잘못된 API 키)
        if 'text/html' in content_type or response_text.startswith('<!doctype html') or response_text.startswith('<html'):
            raise Exception("DART API 인증 실패: API_KEY가 올바르지 않거나 설정되지 않았습니다.")
        
        # ZIP 파일인지 확인
        if not response.content.startswith(b'PK'):
            raise Exception("다운로드한 파일이 ZIP 형식이 아닙니다.")
        
        results = []
        
        # ZIP 파일 압축 해제 및 XML 파싱
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # 파일 목록 확인
                file_list = z.namelist()
                
                # CORPCODE.xml 파일 찾기 (대소문자 구분 없이)
                xml_file = None
                for fname in file_list:
                    if fname.upper() == 'CORPCODE.XML':
                        xml_file = fname
                        break
                
                if not xml_file:
                    raise Exception(f"ZIP 파일에 CORPCODE.xml이 없습니다.")
                
                # CORPCODE.xml 파일 열기
                with z.open(xml_file) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    
                    # 검색어가 포함된 기업 찾기
                    for child in root:
                        corp_name_elem = child.find('corp_name')
                        if corp_name_elem is not None and corp_name_elem.text:
                            # 검색어가 기업 이름에 포함되어 있는지 확인 (대소문자 구분 없이)
                            if search_term.lower() in corp_name_elem.text.lower():
                                corp_code_elem = child.find('corp_code')
                                if corp_code_elem is not None:
                                    results.append({
                                        'corp_name': corp_name_elem.text,
                                        'corp_code': corp_code_elem.text
                                    })
                                    # limit에 도달하면 중단
                                    if len(results) >= limit:
                                        break
        except zipfile.BadZipFile as e:
            raise Exception(f"다운로드한 파일이 올바른 ZIP 형식이 아닙니다.")
        
        return results
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"기업 검색 중 네트워크 오류 발생: {str(e)}")
    except ET.ParseError as e:
        raise Exception(f"XML 파싱 중 오류 발생: {str(e)}")

def get_finance_data(corp_code, bsns_year='2024'):
    """
    기업 코드를 이용하여 재무제표 데이터를 조회합니다.
    사업보고서에는 당기, 전기, 전전기 데이터가 모두 포함됩니다.
    
    Args:
        corp_code (str): 기업 코드
        bsns_year (str): 사업년도 (기본값: '2024')
        
    Returns:
        dict: 재무제표 데이터 (JSON 응답)
    """
    if not API_KEY:
        raise ValueError("API_KEY 환경변수가 설정되지 않았습니다.")
    
    if not corp_code:
        raise ValueError("기업 코드가 제공되지 않았습니다.")
    
    # 재무제표 조회 URL
    url = f'{BASE_URL}/fnlttSinglAcntAll.json'
    
    # 파라미터 설정
    # 사업보고서에는 당기, 전기, 전전기 데이터가 모두 포함됨
    # sj_div='BS'로 재무상태표만 조회하여 데이터량 감소 및 조회 시간 단축
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bsns_year': str(bsns_year),  # 사업년도
        'reprt_code': '11011',  # 사업보고서
        'fs_div': 'CFS',  # 연결재무제표
        'sj_div': 'BS'  # 재무상태표만 조회 (BS: 재무상태표, IS: 손익계산서, CF: 현금흐름표, SC: 자본변동표)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # API 오류 체크
        if data.get('status') == '000':
            return data
        else:
            error_message = data.get('message', '알 수 없는 오류')
            raise Exception(f"DART API 오류: {error_message}")
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"재무제표 데이터 조회 중 오류 발생: {str(e)}")
    except ValueError as e:
        raise Exception(f"JSON 파싱 중 오류 발생: {str(e)}")

def get_finance_dataframe(corp_name):
    """
    기업 이름을 입력받아 재무제표 데이터를 조회하고,
    필요한 필드만 추출하여 판다스 DataFrame으로 반환합니다.
    
    추출 필드:
    - 기업 이름 (corp_name)
    - 기업 코드 (corp_code)
    - 계정과목 이름 (account_nm)
    - 당기 금액 (thstrm_amount) - 당기 행만 추출
    
    재무상태표(sj_div='BS')만 조회되며, sj_div 컬럼은 결과에서 제외됩니다.
    
    Args:
        corp_name (str): 기업 이름
        
    Returns:
        pd.DataFrame: 추출된 재무제표 데이터 (기업 이름, 기업 코드, 계정과목 이름, 당기 금액)
        재무상태표(BS) 데이터만 포함됩니다.
    """
    if not corp_name:
        raise ValueError("기업 이름이 제공되지 않았습니다.")
    
    # 기업 코드 조회
    corp_code = get_corp_code(corp_name)
    if not corp_code:
        raise ValueError(f"기업 '{corp_name}'을 찾을 수 없습니다.")
    
    # 재무제표 데이터 조회 (2024년)
    finance_data = get_finance_data(corp_code, '2024')
    
    # 응답 데이터에서 리스트 추출
    if 'list' not in finance_data or not finance_data['list']:
        raise Exception("재무제표 데이터가 없습니다.")
    
    # DataFrame 생성
    df = pd.DataFrame(finance_data['list'])
    
    # sj_div가 'BS'인 것만 필터링 (재무상태표만, API 파라미터로 이미 필터링되었지만 안전장치)
    if 'sj_div' in df.columns:
        df = df[df['sj_div'] == 'BS'].copy()
    
    # 당기 행만 필터링 (thstrm_amount가 있는 행만)
    df = df[df['thstrm_amount'].notna()]
    
    # 필요한 컬럼만 선택 (sj_div는 제외 - 이미 필터링되었으므로 불필요)
    required_columns = ['corp_code', 'account_nm', 'thstrm_amount']
    
    # 존재하는 컬럼만 선택
    available_columns = [col for col in required_columns if col in df.columns]
    df = df[available_columns].copy()
    
    # 기업 이름 컬럼 추가
    df['corp_name'] = corp_name
    
    # 컬럼 순서 재정렬: 기업 이름, 기업 코드, 계정과목 이름, 당기 금액
    column_order = ['corp_name', 'corp_code', 'account_nm', 'thstrm_amount']
    df = df[column_order]
    
    # 데이터 타입 정리
    df['thstrm_amount'] = pd.to_numeric(df['thstrm_amount'], errors='coerce')
    
    return df

def get_finance_dataframe_10years(corp_name):
    """
    기업 이름을 입력받아 최근 10년치 재무제표 데이터를 조회하고,
    필요한 필드만 추출하여 판다스 DataFrame으로 반환합니다.
    
    시작 연도는 시스템 날짜의 전년도로 자동 설정됩니다.
    예: 현재가 2025년이면 2024년부터 시작하여 10년치 데이터 조회
    
    DART API는 한 번의 요청으로 당기, 전기, 전전기 데이터를 제공하므로,
    3년 단위로 조회하여 효율적으로 데이터를 수집합니다.
    
    조회 전략 (예: 시작 연도가 2024년인 경우):
    - 2024년 조회 → 2024, 2023, 2022 데이터
    - 2021년 조회 → 2021, 2020, 2019 데이터
    - 2018년 조회 → 2018, 2017, 2016 데이터
    - 2015년 조회 → 2015 데이터만 (10년치까지만 필요)
    
    추출 필드:
    - 기업 이름 (corp_name)
    - 기업 코드 (corp_code)
    - 계정과목 코드 (account_id)
    - 계정과목 이름 (account_nm)
    - 금액 (amount)
    - 연도 (year)
    
    Args:
        corp_name (str): 기업 이름
        
    Returns:
        pd.DataFrame: 추출된 재무제표 데이터 (corp_name, corp_code, account_id, account_nm, amount, year)
        재무상태표(BS) 데이터만 포함되며, 최근 10년치 데이터가 포함됩니다.
    """
    if not corp_name:
        raise ValueError("기업 이름이 제공되지 않았습니다.")
    
    # 기업 코드 조회
    corp_code = get_corp_code(corp_name)
    if not corp_code:
        raise ValueError(f"기업 '{corp_name}'을 찾을 수 없습니다.")
    
    # 시스템 날짜의 전년도를 시작 연도로 설정
    current_year = datetime.now().year
    start_year = current_year - 1
    end_year = start_year - 9  # 10년치 데이터
    
    # 조회할 연도 목록 계산 (3년 단위로 조회)
    # 시작 연도부터 역순으로 3년씩 건너뛰며 조회
    query_years = []
    year = start_year
    while year >= end_year:
        query_years.append(year)
        year -= 3
    
    # 마지막 연도가 포함되도록 확인
    if query_years[-1] > end_year:
        query_years.append(end_year)
    
    query_years.sort(reverse=True)  # 내림차순 정렬
    all_dataframes = []
    
    for query_year in query_years:
        try:
            # 재무제표 데이터 조회
            finance_data = get_finance_data(corp_code, str(query_year))
            
            # 응답 데이터에서 리스트 추출
            if 'list' not in finance_data or not finance_data['list']:
                continue  # 데이터가 없으면 건너뛰기
            
            # DataFrame 생성
            df = pd.DataFrame(finance_data['list'])
            
            # sj_div가 'BS'인 것만 필터링
            if 'sj_div' in df.columns:
                df = df[df['sj_div'] == 'BS'].copy()
            
            # 필요한 컬럼 확인
            required_cols = ['corp_code', 'account_id', 'account_nm']
            if not all(col in df.columns for col in required_cols):
                continue
            
            # 각 연도별 데이터 추출
            # thstrm_amount: 당기, frmtrm_amount: 전기, bfefrmtrm_amount: 전전기
            
            dfs_for_year = []
            
            # 당기 데이터 (query_year)
            if 'thstrm_amount' in df.columns:
                df_thstrm = df[df['thstrm_amount'].notna()].copy()
                if not df_thstrm.empty:
                    df_thstrm['amount'] = pd.to_numeric(df_thstrm['thstrm_amount'], errors='coerce')
                    df_thstrm['year'] = query_year
                    dfs_for_year.append(df_thstrm[required_cols + ['amount', 'year']])
            
            # 전기 데이터 (query_year - 1)
            if query_year > 2015 and 'frmtrm_amount' in df.columns:
                df_frmtrm = df[df['frmtrm_amount'].notna()].copy()
                if not df_frmtrm.empty:
                    df_frmtrm['amount'] = pd.to_numeric(df_frmtrm['frmtrm_amount'], errors='coerce')
                    df_frmtrm['year'] = query_year - 1
                    dfs_for_year.append(df_frmtrm[required_cols + ['amount', 'year']])
            
            # 전전기 데이터 (query_year - 2)
            if query_year > 2016 and 'bfefrmtrm_amount' in df.columns:
                df_bfefrm = df[df['bfefrmtrm_amount'].notna()].copy()
                if not df_bfefrm.empty:
                    df_bfefrm['amount'] = pd.to_numeric(df_bfefrm['bfefrmtrm_amount'], errors='coerce')
                    df_bfefrm['year'] = query_year - 2
                    dfs_for_year.append(df_bfefrm[required_cols + ['amount', 'year']])
            
            # 해당 조회 연도의 모든 데이터 합치기
            if dfs_for_year:
                year_df = pd.concat(dfs_for_year, ignore_index=True)
                # end_year 이상의 데이터만 포함 (10년치만)
                year_df = year_df[year_df['year'] >= end_year]
                all_dataframes.append(year_df)
        
        except Exception as e:
            # 특정 연도 조회 실패 시 경고만 출력하고 계속 진행
            print(f"경고: {query_year}년 데이터 조회 실패 - {str(e)}")
            continue
    
    # 모든 연도 데이터 합치기
    if not all_dataframes:
        raise Exception("조회된 재무제표 데이터가 없습니다.")
    
    result_df = pd.concat(all_dataframes, ignore_index=True)
    
    # 기업 이름 컬럼 추가
    result_df['corp_name'] = corp_name
    
    # 중복 제거 (같은 계정과목, 같은 연도가 여러 번 나타날 수 있음)
    result_df = result_df.drop_duplicates(subset=['corp_code', 'account_id', 'account_nm', 'year'], keep='first')
    
    # 컬럼 순서 재정렬: 기업 이름, 기업 코드, 계정과목 코드, 계정과목 이름, 금액, 연도
    column_order = ['corp_name', 'corp_code', 'account_id', 'account_nm', 'amount', 'year']
    result_df = result_df[column_order]
    
    # 최신 연도(시작 연도)의 계정과목 순서를 기준으로 정렬
    # 연도 내림차순 우선, 그 안에서 계정과목 순서 일관성 유지
    latest_year_df = result_df[result_df['year'] == start_year].copy()
    if not latest_year_df.empty:
        # 최신 연도의 계정과목 순서를 유지하기 위한 순서 매핑 생성
        account_order = {account: idx for idx, account in enumerate(latest_year_df['account_nm'].unique())}
        
        # account_nm에 순서 매핑 추가 (없는 경우 큰 값으로 설정하여 뒤로)
        max_order = len(account_order)
        result_df['account_order'] = result_df['account_nm'].map(lambda x: account_order.get(x, max_order))
        
        # 연도 내림차순 우선, 그 다음 계정과목 순서로 정렬
        result_df = result_df.sort_values(['year', 'account_order'], ascending=[False, True])
        
        # 임시 컬럼 제거
        result_df = result_df.drop(columns=['account_order'])
    else:
        # 최신 연도 데이터가 없으면 연도만 정렬
        result_df = result_df.sort_values('year', ascending=False)
    
    return result_df

def read_readme():
    """
    README.md 파일을 읽어서 내용을 반환합니다.
    
    Returns:
        str: README.md 파일 내용, 파일을 찾을 수 없거나 읽는 중 오류가 발생하면 오류 메시지
    """
    readme_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "README.md 파일을 찾을 수 없습니다."
    except Exception as e:
        return f"README.md 파일을 읽는 중 오류가 발생했습니다: {str(e)}"

def prepare_data_for_insert(corp_name):
    """
    기업 이름을 받아서 데이터베이스 삽입을 위한 데이터를 준비합니다.
    
    DataFrame을 처리하고, NaN 값을 처리하며, 중복 체크 및 기존 데이터 삭제 로직을 수행합니다.
    
    Args:
        corp_name (str): 기업 이름
        
    Returns:
        tuple: (success: bool, message: str, insert_values: list, is_update: bool)
            - success: 성공 여부
            - message: 결과 메시지
            - insert_values: 삽입할 데이터 리스트 (성공 시)
            - is_update: 갱신 여부 (기존 데이터가 있었는지)
    """
    if not corp_name:
        return False, '기업 이름이 필요합니다.', None, False
    
    try:
        # 기업 이름으로 다시 데이터 조회
        df = get_finance_dataframe_10years(corp_name)
        
        if df.empty:
            return False, '저장할 데이터가 없습니다.', None, False
        
        # 기업 코드 추출 (첫 번째 행에서)
        corp_code = df.iloc[0]['corp_code'] if not df.empty else None
        if not corp_code:
            return False, '기업 코드를 찾을 수 없습니다.', None, False
        
        # 삽입하려는 데이터의 최근 연도 확인
        latest_year_to_insert = int(df['year'].max())
        
        # DB에서 해당 기업 코드의 최근 연도 확인 (db 모듈 import 필요)
        db_latest_year = db.get_latest_year_by_corp_code(corp_code)
        
        # 기존 데이터가 있고 최근 연도가 같으면 중복 메시지
        if db_latest_year is not None and db_latest_year == latest_year_to_insert:
            return False, '이미 데이터가 등록된 기업입니다.', None, False
        
        is_update = False
        # 기존 데이터가 있고 최근 연도가 다르면 기존 데이터 삭제 후 새로 삽입
        if db_latest_year is not None and db_latest_year != latest_year_to_insert:
            delete_success = db.delete_data_by_corp_code(corp_code)
            if not delete_success:
                return False, '기존 데이터 삭제 중 오류가 발생했습니다.', None, False
            is_update = True
        
        # DataFrame을 튜플 리스트로 변환 (db.insert_data에 맞는 형식)
        # 컬럼 순서: corp_name, corp_code, account_id, account_nm, amount, year
        insert_values = []
        for row in df.to_dict('records'):
            # NaN 값 처리
            amount = row.get('amount')
            year = row.get('year')
            
            # amount 처리 (NaN이면 None)
            if amount is None or (isinstance(amount, float) and math.isnan(amount)):
                amount_value = None
            else:
                try:
                    amount_value = int(float(amount))
                except (ValueError, TypeError):
                    amount_value = None
            
            # year 처리 (NaN이면 None)
            if year is None or (isinstance(year, float) and math.isnan(year)):
                year_value = None
            else:
                try:
                    year_value = int(float(year))
                except (ValueError, TypeError):
                    year_value = None
            
            # account_id 처리 (NaN이면 None)
            account_id = row.get('account_id', '')
            if account_id is None or (isinstance(account_id, float) and math.isnan(account_id)) or account_id == '':
                account_id_value = None
            else:
                account_id_value = str(account_id)
            
            insert_values.append((
                row.get('corp_name', ''),
                row.get('corp_code', ''),
                account_id_value,
                row.get('account_nm', ''),
                amount_value,
                year_value
            ))
        
        return True, '', insert_values, is_update
    
    except Exception as e:
        return False, f'데이터 준비 중 오류가 발생했습니다: {str(e)}', None, False

def export_data_to_csv():
    """
    데이터베이스의 모든 데이터를 CSV 형식으로 내보냅니다.
    
    Returns:
        tuple: (df: pd.DataFrame, columns: list)
            - df: CSV로 변환할 DataFrame
            - columns: 컬럼 이름 리스트
    """
    rows = db.get_all_data()
    
    df = pd.DataFrame(rows, columns=[
        "기업 이름",
        "계정과목 코드",
        "회계 항목명",
        "금액",
        "년도"
    ])
    
    return df

def export_data_to_json():
    """
    데이터베이스의 모든 데이터를 JSON 형식으로 내보냅니다.
    
    Returns:
        str: JSON 문자열 (UTF-8 인코딩)
    """
    rows = db.get_all_data()
    
    df = pd.DataFrame(rows, columns=[
        "기업 이름",
        "계정과목 코드",
        "회계 항목명",
        "금액",
        "년도"
    ])
    
    json_str = df.to_json(force_ascii=False, orient="records", indent=4)
    return json_str

def scikit():
    rows = db.get_all_data()
    
    if not rows:
        raise ValueError("저장된 재무 데이터가 없습니다. 먼저 기업 데이터를 저장해주세요.")
    
    df = pd.DataFrame(rows, columns=["corp_name", "account_id", "account_nm", "amount", "year"])
    
    # account_id가 None인 데이터 제거
    df = df[df["account_id"].notna()].copy()
    
    if df.empty:
        raise ValueError("계정과목 코드가 있는 데이터가 없습니다.")
    
    TARGET_IDS = [
        "ifrs-full_Assets",      # 자산총계
        "ifrs-full_Equity",      # 자본총계
        "ifrs-full_Liabilities"  # 부채총계
    ]

    # ✅ 입력값(Feature) 계정 ID
    COMMON_IDS = [
        "ifrs-full_CurrentAssets",
        "ifrs-full_NoncurrentAssets",
        "ifrs-full_CashAndCashEquivalents",
        "ifrs-full_Inventories",
        "ifrs-full_PropertyPlantAndEquipment",
        "ifrs-full_IntangibleAssetsAndGoodwill",
        "ifrs-full_CurrentTradeReceivables",
        "ifrs-full_OtherCurrentAssets",

        "ifrs-full_CurrentLiabilities",
        "ifrs-full_NoncurrentLiabilities",
        "ifrs-full_LongtermBorrowings",
        "ifrs-full_CurrentProvisions",
        "ifrs-full_OtherCurrentLiabilities",
        "ifrs-full_DeferredTaxLiabilities",

        "ifrs-full_IssuedCapital",
        "ifrs-full_RetainedEarnings",
        "ifrs-full_SharePremium",
        "ifrs-full_NoncontrollingInterests"
    ]

    # ✅ 타겟 데이터 (정답)
    target_df = df[df["account_id"].isin(TARGET_IDS)]

    # ✅ 학습 데이터 (입력값)
    feature_df = df[df["account_id"].isin(COMMON_IDS)]
    
    if target_df.empty:
        raise ValueError("목표 계정 ID(자산총계, 자본총계, 부채총계) 데이터가 없습니다.")
    
    if feature_df.empty:
        raise ValueError("입력 계정 ID 데이터가 없습니다.")

    # ✅ Pivot 생성 (account_id 기준)
    pivot = feature_df.pivot_table(
        index=["corp_name","year"],
        columns="account_id",
        values="amount",
        aggfunc="sum"
    ).fillna(0).reset_index()
    
    return pivot, target_df

def train_model(pivot, target_df):
    # ✅ 타겟 pivot (account_id 기준)
    target_pivot = target_df.pivot_table(
        index=["corp_name","year"],
        columns="account_id",
        values="amount",
        aggfunc="sum"
    ).reset_index()

    # ✅ feature + target merge
    train_df = pd.merge(pivot, target_pivot, on=["corp_name","year"])
    
    # 데이터 검증
    if train_df.empty:
        raise ValueError("학습할 데이터가 없습니다. 재무 데이터를 먼저 저장해주세요.")

    # ✅ Feature 계정 ID
    COMMON_IDS = [
        "ifrs-full_CurrentAssets",
        "ifrs-full_NoncurrentAssets",
        "ifrs-full_CashAndCashEquivalents",
        "ifrs-full_Inventories",
        "ifrs-full_PropertyPlantAndEquipment",
        "ifrs-full_IntangibleAssetsAndGoodwill",
        "ifrs-full_CurrentTradeReceivables",
        "ifrs-full_OtherCurrentAssets",

        "ifrs-full_CurrentLiabilities",
        "ifrs-full_NoncurrentLiabilities",
        "ifrs-full_LongtermBorrowings",
        "ifrs-full_CurrentProvisions",
        "ifrs-full_OtherCurrentLiabilities",
        "ifrs-full_DeferredTaxLiabilities",

        "ifrs-full_IssuedCapital",
        "ifrs-full_RetainedEarnings",
        "ifrs-full_SharePremium",
        "ifrs-full_NoncontrollingInterests"
    ]

    # ✅ Target 계정 ID
    TARGET_IDS = [
        "ifrs-full_Assets",
        "ifrs-full_Equity",
        "ifrs-full_Liabilities"
    ]

    # 필수 계정 ID 검증
    missing_feature_ids = [cid for cid in COMMON_IDS if cid not in train_df.columns]
    missing_target_ids = [tid for tid in TARGET_IDS if tid not in train_df.columns]
    
    if missing_feature_ids or missing_target_ids:
        error_msg = "필수 계정 ID가 없습니다. "
        if missing_feature_ids:
            error_msg += f"입력 계정: {', '.join(missing_feature_ids[:3])}{'...' if len(missing_feature_ids) > 3 else ''}. "
        if missing_target_ids:
            error_msg += f"목표 계정: {', '.join(missing_target_ids)}."
        raise ValueError(error_msg)

    # ✅ 입력(X), 정답(y)
    X = train_df[COMMON_IDS]
    y = train_df[TARGET_IDS]
    
    # NaN 값 확인
    if X.isna().any().any() or y.isna().any().any():
        raise ValueError("데이터에 결측값이 있습니다. 모든 계정 ID의 데이터가 필요합니다.")

    # 학습 데이터와 검증 데이터 분리 (80% 학습, 20% 검증)
    # 데이터가 너무 적으면 분리하지 않음 (최소 5개 이상 필요)
    if len(X) >= 5:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=True
        )
    else:
        # 데이터가 적으면 학습 데이터로만 평가 (과적합 경고 포함)
        X_train, X_val = X, X
        y_train, y_val = y, y
    
    # ✅ 모델 학습
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # 검증 데이터로 성능 지표 계산 (일반화 성능 평가)
    y_pred = model.predict(X_val)
    y_true = y_val
    
    # 각 타겟 변수별 성능 지표 계산
    metrics = {}
    target_names = ["자산총계", "자본총계", "부채총계"]
    
    # 데이터 분리 여부 확인
    is_split = len(X) >= 5
    
    for i, target_name in enumerate(target_names):
        y_true_col = y_true.iloc[:, i].values if hasattr(y_true, 'iloc') else y_true[:, i]
        y_pred_col = y_pred[:, i]
        
        # 결정계수 (R²)
        r2 = r2_score(y_true_col, y_pred_col)
        
        # 평균 제곱 오차 (MSE)
        mse = mean_squared_error(y_true_col, y_pred_col)
        
        # 평균 절대 오차 (MAE)
        mae = mean_absolute_error(y_true_col, y_pred_col)
        
        # 평균 제곱근 오차 (RMSE)
        rmse = np.sqrt(mse)
        
        metrics[target_name] = {
            'r2': r2,
            'mse': mse,
            'mae': mae,
            'rmse': rmse
        }
    
    # 전체 평균 성능 지표
    avg_r2 = np.mean([metrics[name]['r2'] for name in target_names])
    avg_rmse = np.mean([metrics[name]['rmse'] for name in target_names])
    avg_mae = np.mean([metrics[name]['mae'] for name in target_names])

    return model, COMMON_IDS, TARGET_IDS, metrics, {
        'avg_r2': avg_r2,
        'avg_rmse': avg_rmse,
        'avg_mae': avg_mae,
        'is_split': is_split,
        'train_size': len(X_train),
        'val_size': len(X_val)
    }

def predict_company(model, pivot, corp_name, COMMON_IDS, TARGET_IDS, target_year=None):
    """
    기업의 재무 지표를 예측합니다.
    
    Args:
        model: 학습된 모델
        pivot: 피벗 테이블 데이터
        corp_name: 기업명
        COMMON_IDS: 입력 계정 ID 리스트
        TARGET_IDS: 목표 계정 ID 리스트
        target_year: 예측할 연도 (None이면 최신 연도 기반)
    
    Returns:
        dict: 예측 결과
    """
    # 기업 데이터 필터링 및 검증
    corp_data = pivot[pivot["corp_name"] == corp_name].copy()
    if corp_data.empty:
        raise ValueError(f"기업 '{corp_name}'의 데이터를 찾을 수 없습니다.")
    
    # 연도순 정렬
    corp_data = corp_data.sort_values("year")
    latest = corp_data.iloc[-1]
    latest_year = int(latest["year"])
    
    # 필수 계정 ID 확인
    missing_ids = [cid for cid in COMMON_IDS if cid not in pivot.columns]
    if missing_ids:
        error_msg = f"필수 계정 ID가 없습니다: {', '.join(missing_ids[:3])}"
        if len(missing_ids) > 3:
            error_msg += f" 외 {len(missing_ids) - 3}개"
        raise ValueError(error_msg)
    
    # NaN 값 확인 (pandas의 isna() 사용)
    X_input_series = latest[COMMON_IDS]
    if X_input_series.isna().any():
        missing_values = [cid for cid in COMMON_IDS if pd.isna(X_input_series[cid])]
        raise ValueError(f"기업 '{corp_name}'의 필수 계정 데이터가 없습니다: {', '.join(missing_values[:3])}")
    
    # 숫자형으로 변환
    X_input_base = pd.to_numeric(X_input_series, errors='coerce').values
    if np.isnan(X_input_base).any():
        missing_values = [COMMON_IDS[i] for i in range(len(COMMON_IDS)) if np.isnan(X_input_base[i])]
        raise ValueError(f"기업 '{corp_name}'의 필수 계정 데이터가 없습니다: {', '.join(missing_values[:3])}")
    
    # 연도별 입력값 조정 (과거 추세 기반)
    if target_year and target_year > latest_year:
        # 연도 차이 계산
        year_diff = target_year - latest_year
        
        # 과거 데이터가 2년 이상 있는 경우 연평균 성장률 계산
        if len(corp_data) >= 2:
            # 최신 연도와 이전 연도 데이터
            prev_year_data = corp_data.iloc[-2]
            prev_X = pd.to_numeric(prev_year_data[COMMON_IDS], errors='coerce').values
            
            # 연평균 성장률 계산 (CAGR)
            # 성장률 = (최신값 / 이전값) ^ (1/연도차이) - 1
            growth_rates = np.where(
                prev_X > 0,
                np.power(X_input_base / prev_X, 1.0 / (latest_year - int(prev_year_data["year"]))) - 1,
                0  # 이전값이 0이면 성장률 0
            )
            
            # 예측 연도까지의 성장률 적용
            # 미래값 = 현재값 * (1 + 성장률) ^ 연도차이
            X_input_adjusted = X_input_base * np.power(1 + growth_rates, year_diff)
        else:
            # 데이터가 부족하면 최신값 그대로 사용
            X_input_adjusted = X_input_base
    else:
        # target_year가 없거나 과거 연도면 최신값 사용
        X_input_adjusted = X_input_base
    
    X_input = X_input_adjusted.reshape(1, -1)

    pred = model.predict(X_input)[0]

    ID_TO_NAME = {
        "ifrs-full_Assets": "자산총계",
        "ifrs-full_Equity": "자본총계",
        "ifrs-full_Liabilities": "부채총계"
    }

    # 예측값 추출 (소수점 유지)
    predicted_assets = pred[0]
    predicted_equity = pred[1]
    predicted_liabilities = pred[2]
    
    # 회계 방정식: 자산 = 부채 + 자본
    # 부채와 자본의 합 계산
    liabilities_plus_equity = predicted_liabilities + predicted_equity
    
    # 자산을 부채+자본 합으로 재조정 (회계 방정식 맞추기)
    # 또는 부채와 자본의 비율을 유지하면서 합이 자산이 되도록 조정
    if abs(predicted_assets - liabilities_plus_equity) > 0.01:  # 차이가 0.01 이상이면 조정
        # 방법 1: 자산을 부채+자본 합으로 재조정
        adjusted_assets = liabilities_plus_equity
        
        # 방법 2: 부채와 자본의 비율을 유지하면서 합이 자산이 되도록 조정
        # (현재는 방법 1 사용)
        # total = predicted_liabilities + predicted_equity
        # if total > 0:
        #     ratio_liabilities = predicted_liabilities / total
        #     ratio_equity = predicted_equity / total
        #     adjusted_liabilities = predicted_assets * ratio_liabilities
        #     adjusted_equity = predicted_assets * ratio_equity
        # else:
        #     adjusted_liabilities = predicted_liabilities
        #     adjusted_equity = predicted_equity
    else:
        adjusted_assets = predicted_assets
    
    # 정수로 변환 (소수점 버림)
    return {
        ID_TO_NAME[TARGET_IDS[0]]: int(adjusted_assets),
        ID_TO_NAME[TARGET_IDS[1]]: int(predicted_equity),
        ID_TO_NAME[TARGET_IDS[2]]: int(predicted_liabilities),
    }

def make_compare_table(compare_list):
    """비교 테이블 생성 함수"""
    from app import db
    import pandas as pd

    dfs = []

    # 1) 각 기업/연도별 데이터 로드
    for item in compare_list:
        corp = item["corp"]
        year = item["year"]

        rows = db.get_data_for_compare(corp, year)
        df = pd.DataFrame(rows)

        if df.empty:
            continue

        df = df[["account_id", "account_nm", "amount"]].copy()
        # 0 또는 "0" 또는 0.0 은 None으로 처리
        df["amount"] = df["amount"].apply(
            lambda x: None if x in [0, 0.0, "0", "0.0"] else x
        )
        df = df.rename(columns={"amount": f"{corp}({year})"})

        dfs.append(df)

    if not dfs:
        return None

    # -------------------------------------------------------------
    # 2) 병합 시작 (첫 번째 df 기준)
    # -------------------------------------------------------------
    result = dfs[0]

    for df in dfs[1:]:
        # 우선 ID 기준 merge
        left_has_id = result["account_id"].notna().any()
        right_has_id = df["account_id"].notna().any()

        if left_has_id and right_has_id:
            # 2-1) account_id 기준 병합
            merged = pd.merge(result, df, on="account_id", how="outer", suffixes=("_l", "_r"))

            # account_nm 정리 (좌/우 중 존재하는 값 선택)
            merged["account_nm"] = merged["account_nm_l"].combine_first(merged["account_nm_r"])
            merged = merged.drop(columns=["account_nm_l", "account_nm_r"])

        else:
            # 2-2) account_nm 기준 병합
            merged = pd.merge(result, df, on="account_nm", how="outer")

        result = merged

    # -------------------------------------------------------------
    # 3) id도 nm도 둘 다 안 겹친 항목 제거 (비교 불가능한 row 제거)
    # -------------------------------------------------------------
    # "비교"가 가능하려면 최소 두 개 이상의 기업 컬럼에서 값이 존재해야 함
    value_cols = [col for col in result.columns if "(" in col and ")" in col]

    result["notnull_count"] = result[value_cols].notna().sum(axis=1)
    result = result[result["notnull_count"] >= 2].copy()
    result = result.drop(columns=["notnull_count"])

    # -------------------------------------------------------------
    # 4) 비교 결과 구성 (표시할 컬럼)
    # -------------------------------------------------------------
    # 표시 컬럼: account_nm + 각 기업 금액
    final_cols = ["account_nm"] + value_cols

    # -------------------------------------------------------------
    # 5) 2개 비교일 때 차이/증감률 계산
    # -------------------------------------------------------------
    if len(compare_list) == 2:
        col1 = f"{compare_list[0]['corp']}({compare_list[0]['year']})"
        col2 = f"{compare_list[1]['corp']}({compare_list[1]['year']})"

        result["차이(금액)"] = result[col2] - result[col1]

        def calc_rate(row):
            base = row[col1]
            if base is None or base == 0:
                return None
            return (row[col2] - base) / base * 100

        result["증감률(%)"] = result.apply(calc_rate, axis=1)

        final_cols += ["차이(금액)", "증감률(%)"]

    # -------------------------------------------------------------
    # 6) 최종 컬럼 반환
    # -------------------------------------------------------------
    return result[final_cols]

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

    # 절대값 기준으로 단위 변환
    abs_num = abs(num)

    if abs_num >= 1_0000_0000_0000:  # 1조
        formatted = f"{num / 1_0000_0000_0000:.1f}조"
    elif abs_num >= 1_0000_0000:  # 1억
        formatted = f"{num / 1_0000_0000:.1f}억"
    else:
        formatted = f"{num:,.0f}"  # 일반 콤마 표시

    return formatted

def make_chart_data(compare_list):
    """
    차트용 데이터 생성
    compare_list = [{"corp": "삼성전자", "year": "2023"}, ...]
    """

    from app import db
    import pandas as pd

    dfs = []

    # 1) 기업별 데이터프레임 생성
    for item in compare_list:
        corp = item["corp"]
        year = item["year"]

        rows = db.get_data_for_compare(corp, year)
        df = pd.DataFrame(rows)

        if df.empty:
            continue

        df = df[["account_nm", "amount"]].copy()
        df = df.rename(columns={"amount": f"{corp}({year})"})

        dfs.append(df)

    if not dfs:
        return {}

    # 2) account_nm 기준으로 모두 merge
    result = dfs[0]
    for df in dfs[1:]:
        result = pd.merge(result, df, on="account_nm", how="outer")

    # 3) NaN은 0으로 (차트는 숫자 필요)
    result = result.fillna(0)

    # 4) 딕셔너리 구조로 변환
    chart_data = {
        "accounts": result["account_nm"].tolist()
    }

    value_cols = [col for col in result.columns if col != "account_nm"]
    for col in value_cols:
        chart_data[col] = result[col].tolist()

    return chart_data

def get_amount_by_account_id(rows, account_id):
    """account_id로 금액을 조회하는 헬퍼 함수"""
    if account_id is None:
        return None
    for row in rows:
        if row[0] == account_id:  # row[0]은 account_id
            return row[2]  # row[2]는 amount
    return None

def find_account_id_by_name(rows, account_name):
    """계정명으로 account_id를 찾는 헬퍼 함수"""
    for row in rows:
        if row[1] == account_name:  # row[1]은 account_nm
            return row[0]  # row[0]은 account_id
    return None

def calculate_financial_indicators(rows):
    """
    재무지표를 계산합니다.
    
    Args:
        rows: 계정 데이터 리스트 [(account_id, account_nm, amount), ...]
        
    Returns:
        dict: 재무지표 딕셔너리
            - current_ratio: 유동비율 (%)
            - debt_ratio: 부채비율 (%) - 부채총계/자산총계
            - equity_ratio: 자기자본비율 (%) - 자본총계/자산총계
            - quick_ratio: 당좌비율 (%) - (유동자산-재고자산)/유동부채
            - debt_to_equity: 부채자본비율 (%) - 부채총계/자본총계
    """
    if not rows:
        return {
            'current_ratio': None,
            'debt_ratio': None,
            'equity_ratio': None,
            'quick_ratio': None,
            'debt_to_equity': None
        }
    
    # 계정명으로 account_id 찾기 (동적 매핑)
    account_ids = {
        '유동자산': find_account_id_by_name(rows, '유동자산'),
        '유동부채': find_account_id_by_name(rows, '유동부채'),
        '부채총계': find_account_id_by_name(rows, '부채총계'),
        '자본총계': find_account_id_by_name(rows, '자본총계'),
        '자산총계': find_account_id_by_name(rows, '자산총계'),
        '재고자산': find_account_id_by_name(rows, '재고자산')
    }
    
    # ID로 금액 조회
    try:
        current_assets = get_amount_by_account_id(rows, account_ids['유동자산'])
        current_liabilities = get_amount_by_account_id(rows, account_ids['유동부채'])
        total_debt = get_amount_by_account_id(rows, account_ids['부채총계'])
        total_equity = get_amount_by_account_id(rows, account_ids['자본총계'])
        total_assets = get_amount_by_account_id(rows, account_ids['자산총계'])
        inventory = get_amount_by_account_id(rows, account_ids['재고자산'])
        
        indicators = {
            'current_ratio': round(current_assets / current_liabilities * 100, 2) 
                            if current_assets is not None and current_liabilities is not None and current_liabilities != 0 else None,
            'debt_ratio': round(total_debt / total_assets * 100, 2) 
                        if total_debt is not None and total_assets is not None and total_assets != 0 else None,
            'equity_ratio': round(total_equity / total_assets * 100, 2) 
                           if total_equity is not None and total_assets is not None and total_assets != 0 else None,
            'quick_ratio': round((current_assets - (inventory if inventory is not None else 0)) / current_liabilities * 100, 2) 
                          if current_assets is not None and current_liabilities is not None and current_liabilities != 0 else None,
            'debt_to_equity': round(total_debt / total_equity * 100, 2) 
                             if total_debt is not None and total_equity is not None and total_equity != 0 else None
        }
    except (ZeroDivisionError, TypeError):
        indicators = {
            'current_ratio': None,
            'debt_ratio': None,
            'equity_ratio': None,
            'quick_ratio': None,
            'debt_to_equity': None
        }
    
    return indicators