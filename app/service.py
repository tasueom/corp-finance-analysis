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
        from app import db
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
    from app import db
    rows = db.get_all_data()
    
    df = pd.DataFrame(rows, columns=[
        "기업 이름",
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
    from app import db
    rows = db.get_all_data()
    
    df = pd.DataFrame(rows, columns=[
        "기업 이름",
        "회계 항목명",
        "금액",
        "년도"
    ])
    
    json_str = df.to_json(force_ascii=False, orient="records", indent=4)
    return json_str