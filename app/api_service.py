"""
DART API 관련 서비스 모듈
기업 코드 조회, 재무제표 데이터 조회 등의 API 호출 담당
"""
import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import os
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# .env 파일 로드
base_dir = Path(__file__).parent.parent
env_paths = [
    base_dir / '.env',
    Path.cwd() / '.env',
    Path('.env')
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        env_loaded = True
        break

if not env_loaded:
    load_dotenv(override=True)

# 환경변수 로드
API_KEY = os.environ.get('API_KEY', '').strip()
BASE_URL = os.environ.get('BASE_URL', 'https://opendart.fss.or.kr/api').strip()

# 기업 코드 캐시 (메모리 캐싱)
_corp_code_cache = {}
_corp_list_cache = []
_cache_loaded = False


def load_corp_code_cache():
    """
    DART API에서 전체 기업 코드 목록을 다운로드하여 메모리에 캐싱합니다.
    Flask 앱 시작 시 백그라운드에서 호출됩니다.
    """
    global _corp_code_cache, _corp_list_cache, _cache_loaded
    
    if not API_KEY:
        print("경고: API_KEY가 설정되지 않아 기업 코드 캐시를 로드할 수 없습니다.")
        return False
    
    try:
        print("기업 코드 캐시 로딩 시작...")
        url = f'{BASE_URL}/corpCode.xml?crtfc_key={API_KEY}'
        
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        if not response.content.startswith(b'PK'):
            print("경고: 다운로드한 파일이 ZIP 형식이 아닙니다.")
            return False
        
        _corp_code_cache = {}
        _corp_list_cache = []
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            xml_file = None
            for fname in z.namelist():
                if fname.upper() == 'CORPCODE.XML':
                    xml_file = fname
                    break
            
            if not xml_file:
                print("경고: ZIP 파일에 CORPCODE.xml이 없습니다.")
                return False
            
            with z.open(xml_file) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                for child in root:
                    corp_name_elem = child.find('corp_name')
                    corp_code_elem = child.find('corp_code')
                    
                    if corp_name_elem is not None and corp_code_elem is not None:
                        corp_name = corp_name_elem.text
                        corp_code = corp_code_elem.text
                        
                        if corp_name and corp_code:
                            _corp_code_cache[corp_name] = corp_code
                            _corp_list_cache.append({
                                'corp_name': corp_name,
                                'corp_code': corp_code
                            })
        
        _cache_loaded = True
        print(f"기업 코드 캐시 로딩 완료: {len(_corp_list_cache)}개 기업")
        return True
        
    except Exception as e:
        print(f"기업 코드 캐시 로딩 실패: {str(e)}")
        return False


def get_corp_code(corp_name):
    """
    기업 이름으로 DART 기업 코드를 조회합니다.
    
    Args:
        corp_name (str): 검색할 기업 이름
        
    Returns:
        str: 기업 코드 (corp_code), 찾지 못한 경우 None
    """
    if _cache_loaded and corp_name in _corp_code_cache:
        return _corp_code_cache[corp_name]
    
    if not _cache_loaded:
        raise Exception(
            "기업 코드 캐시가 아직 로드되지 않았습니다. "
            "잠시 후 다시 시도해주세요. (서버 시작 중일 수 있습니다)"
        )
    
    return None


def search_corps(search_term, limit=50):
    """
    검색어가 포함된 기업 목록을 조회합니다.
    
    Args:
        search_term (str): 검색할 기업 이름 (부분 일치)
        limit (int): 최대 반환 개수 (기본값: 50)
        
    Returns:
        list: 기업 정보 리스트 [{'corp_name': '기업명', 'corp_code': '기업코드'}, ...]
    """
    if not search_term or len(search_term.strip()) < 1:
        return []
    
    if not _cache_loaded:
        return []
    
    search_term = search_term.strip().lower()
    results = []
    
    for corp in _corp_list_cache:
        if search_term in corp['corp_name'].lower():
            results.append(corp)
            if len(results) >= limit:
                break
    
    return results


def get_finance_data(corp_code, bsns_year='2024'):
    """
    기업 코드를 이용하여 재무제표 데이터를 조회합니다.
    
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
    
    url = f'{BASE_URL}/fnlttSinglAcntAll.json'
    
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bsns_year': str(bsns_year),
        'reprt_code': '11011',  # 사업보고서
        'fs_div': 'CFS',  # 연결재무제표
        'sj_div': 'BS'  # 재무상태표만 조회
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
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
    기업 이름을 입력받아 재무제표 데이터를 조회하고 DataFrame으로 반환합니다.
    
    Args:
        corp_name (str): 기업 이름
        
    Returns:
        pd.DataFrame: 추출된 재무제표 데이터
    """
    if not corp_name:
        raise ValueError("기업 이름이 제공되지 않았습니다.")
    
    corp_code = get_corp_code(corp_name)
    if not corp_code:
        raise ValueError(f"기업 '{corp_name}'을 찾을 수 없습니다.")
    
    finance_data = get_finance_data(corp_code, '2024')
    
    if 'list' not in finance_data or not finance_data['list']:
        raise Exception("재무제표 데이터가 없습니다.")
    
    df = pd.DataFrame(finance_data['list'])
    
    if 'sj_div' in df.columns:
        df = df[df['sj_div'] == 'BS'].copy()
    
    df = df[df['thstrm_amount'].notna()]
    
    required_columns = ['corp_code', 'account_nm', 'thstrm_amount']
    available_columns = [col for col in required_columns if col in df.columns]
    df = df[available_columns].copy()
    
    df['corp_name'] = corp_name
    
    column_order = ['corp_name', 'corp_code', 'account_nm', 'thstrm_amount']
    df = df[column_order]
    
    df['thstrm_amount'] = pd.to_numeric(df['thstrm_amount'], errors='coerce')
    
    return df


def get_finance_dataframe_10years(corp_name):
    """
    기업 이름을 입력받아 최근 10년치 재무제표 데이터를 조회하고 DataFrame으로 반환합니다.
    
    Args:
        corp_name (str): 기업 이름
        
    Returns:
        pd.DataFrame: 추출된 재무제표 데이터
    """
    if not corp_name:
        raise ValueError("기업 이름이 제공되지 않았습니다.")
    
    corp_code = get_corp_code(corp_name)
    if not corp_code:
        raise ValueError(f"기업 '{corp_name}'을 찾을 수 없습니다.")
    
    current_year = datetime.now().year
    
    # 첫 번째 결과가 나올 때까지 start_year를 감소시키며 반복
    result_df = None
    for offset in range(1, 3):  # current_year - 1, current_year - 2까지 시도
        start_year = current_year - offset
        end_year = start_year - 9
        result_df = _fetch_finance_dataframe(corp_code, corp_name, start_year, end_year)
        
        # 결과가 있고 start_year 데이터가 있으면 성공
        if result_df is not None and not result_df.empty and not result_df[result_df['year'] == start_year].empty:
            break
    
    if result_df is None or result_df.empty:
        raise Exception("조회된 재무제표 데이터가 없습니다.")
    
    return result_df


def _fetch_finance_dataframe(corp_code, corp_name, start_year, end_year):
    """
    지정된 연도 범위로 재무제표 데이터를 조회하는 내부 함수
    
    Args:
        corp_code (str): 기업 코드
        corp_name (str): 기업 이름
        start_year (int): 시작 연도
        end_year (int): 종료 연도
        
    Returns:
        pd.DataFrame: 추출된 재무제표 데이터 (실패 시 None)
    """
    query_years = []
    year = start_year
    while year >= end_year:
        query_years.append(year)
        year -= 3
    
    if query_years[-1] > end_year:
        query_years.append(end_year)
    
    query_years.sort(reverse=True)
    all_dataframes = []
    
    for query_year in query_years:
        try:
            finance_data = get_finance_data(corp_code, str(query_year))
            
            if 'list' not in finance_data or not finance_data['list']:
                continue
            
            df = pd.DataFrame(finance_data['list'])
            
            if 'sj_div' in df.columns:
                df = df[df['sj_div'] == 'BS'].copy()
            
            required_cols = ['corp_code', 'account_id', 'account_nm']
            if not all(col in df.columns for col in required_cols):
                continue
            
            dfs_for_year = []
            
            if 'thstrm_amount' in df.columns:
                df_thstrm = df[df['thstrm_amount'].notna()].copy()
                if not df_thstrm.empty:
                    df_thstrm['amount'] = pd.to_numeric(df_thstrm['thstrm_amount'], errors='coerce')
                    df_thstrm['year'] = query_year
                    dfs_for_year.append(df_thstrm[required_cols + ['amount', 'year']])
            
            if query_year > 2015 and 'frmtrm_amount' in df.columns:
                df_frmtrm = df[df['frmtrm_amount'].notna()].copy()
                if not df_frmtrm.empty:
                    df_frmtrm['amount'] = pd.to_numeric(df_frmtrm['frmtrm_amount'], errors='coerce')
                    df_frmtrm['year'] = query_year - 1
                    dfs_for_year.append(df_frmtrm[required_cols + ['amount', 'year']])
            
            if query_year > 2016 and 'bfefrmtrm_amount' in df.columns:
                df_bfefrm = df[df['bfefrmtrm_amount'].notna()].copy()
                if not df_bfefrm.empty:
                    df_bfefrm['amount'] = pd.to_numeric(df_bfefrm['bfefrmtrm_amount'], errors='coerce')
                    df_bfefrm['year'] = query_year - 2
                    dfs_for_year.append(df_bfefrm[required_cols + ['amount', 'year']])
            
            if dfs_for_year:
                year_df = pd.concat(dfs_for_year, ignore_index=True)
                year_df = year_df[year_df['year'] >= end_year]
                all_dataframes.append(year_df)
        
        except Exception as e:
            print(f"경고: {query_year}년 데이터 조회 실패 - {str(e)}")
            continue
    
    if not all_dataframes:
        return None
    
    result_df = pd.concat(all_dataframes, ignore_index=True)
    result_df['corp_name'] = corp_name
    
    result_df = result_df.drop_duplicates(subset=['corp_code', 'account_id', 'account_nm', 'year'], keep='first')
    
    column_order = ['corp_name', 'corp_code', 'account_id', 'account_nm', 'amount', 'year']
    result_df = result_df[column_order]
    
    latest_year_df = result_df[result_df['year'] == start_year].copy()
    if not latest_year_df.empty:
        account_order = {account: idx for idx, account in enumerate(latest_year_df['account_nm'].unique())}
        max_order = len(account_order)
        result_df['account_order'] = result_df['account_nm'].map(lambda x: account_order.get(x, max_order))
        result_df = result_df.sort_values(['year', 'account_order'], ascending=[False, True])
        result_df = result_df.drop(columns=['account_order'])
    else:
        result_df = result_df.sort_values('year', ascending=False)
    
    return result_df

