import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import os

API_KEY = os.environ.get('API_KEY')
BASE_URL = os.environ.get('BASE_URL', 'https://opendart.fss.or.kr/api')

def get_corp_code(corp_name):
    """
    기업 이름으로 DART 기업 코드를 조회합니다.
    
    Args:
        corp_name (str): 검색할 기업 이름
        
    Returns:
        str: 기업 코드 (corp_code), 찾지 못한 경우 None
    """
    if not API_KEY:
        raise ValueError("API_KEY 환경변수가 설정되지 않았습니다.")
    
    # corpCode.xml 다운로드 URL
    url = f'{BASE_URL}/corpCode.xml?crtfc_key={API_KEY}'
    
    try:
        # ZIP 파일로 압축된 XML 다운로드
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # ZIP 파일 압축 해제 및 XML 파싱
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # CORPCODE.xml 파일 열기
            with z.open('CORPCODE.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                # 기업 이름으로 검색
                for child in root:
                    corp_name_elem = child.find('corp_name')
                    if corp_name_elem is not None and corp_name_elem.text == corp_name:
                        corp_code_elem = child.find('corp_code')
                        if corp_code_elem is not None:
                            return corp_code_elem.text
        
        return None
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"기업 코드 조회 중 오류 발생: {str(e)}")
    except zipfile.BadZipFile:
        raise Exception("다운로드한 파일이 올바른 ZIP 형식이 아닙니다.")
    except ET.ParseError as e:
        raise Exception(f"XML 파싱 중 오류 발생: {str(e)}")

def get_finance_data(corp_code):
    """
    기업 코드를 이용하여 재무제표 데이터를 조회합니다.
    사업년도 2024, 보고서 코드 11011(사업보고서), 재무제표 구분 CFS(연결재무제표)
    사업보고서에는 당기(2024년)와 전기(2023년) 데이터가 모두 포함됩니다.
    
    Args:
        corp_code (str): 기업 코드
        
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
    # 사업년도 2024, 보고서 코드 11011(사업보고서), 재무제표 구분 CFS(연결재무제표)
    # 사업보고서에는 당기(2024년)와 전기(2023년) 데이터가 모두 포함됨
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bsns_year': '2024',  # 사업년도 2024
        'reprt_code': '11011',  # 사업보고서
        'fs_div': 'CFS'  # 연결재무제표
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