import mysql.connector
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

base_config = {
    "host": os.environ.get('DB_HOST', 'localhost'),
    "user": os.environ.get('DB_USER', 'root'),
    "password": os.environ.get('DB_PASSWORD'),
}

DB_NAME = os.environ.get('DB_NAME', 'default_db')

TABLE_NAME = os.environ.get('TABLE_NAME', 'corp_finance')

def get_conn():
    """커넥션과 커서 반환하는 함수"""
    return mysql.connector.connect(**base_config, database=DB_NAME)

def create_database():
    """데이터베이스를 생성하고 성공 여부를 반환합니다."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**base_config)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Database creation failed: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        # 리소스 정리: 예외 발생 여부와 관계없이 항상 실행
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def drop_table():
    """테이블을 삭제하고 성공 여부를 반환합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        # 외래키 체크를 일시적으로 비활성화하여 어떤 순서로든 삭제 가능하도록 함
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DROP TABLE IF EXISTS students")
        cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Table drop failed: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_table():
    """테이블을 생성하고 성공 여부를 반환합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        # students 테이블 생성 (먼저 생성해야 외래키 참조 가능)
        cursor.execute(f"""
            CREATE TABLE {TABLE_NAME} (
                id int primary key auto_increment,
                corp_name varchar(100),
                corp_code varchar(20),
                account_id varchar(300),
                account_nm varchar(100),
                amount bigint,
                year int
            );
        """)
        
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Table creation failed: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        # 리소스 정리: 예외 발생 여부와 관계없이 항상 실행
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_latest_year_by_corp_code(corp_code):
    """기업 코드로 최근 연도를 조회합니다. 데이터가 없으면 None을 반환합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX(year) FROM {TABLE_NAME} WHERE corp_code = %s", (corp_code,))
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else None
    except mysql.connector.Error as err:
        print(f"Get latest year failed: {err}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_data_by_corp_code(corp_code):
    """기업 코드로 해당 기업의 모든 데이터를 삭제합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE corp_code = %s", (corp_code,))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Data deletion failed: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_data(data):
    """데이터를 삽입하고 성공 여부를 반환합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.executemany(f"INSERT INTO {TABLE_NAME} (corp_name, corp_code, account_id, account_nm, amount, year) VALUES (%s, %s, %s, %s, %s, %s)", data)
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Data insertion failed: {err}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_corp_list():
    """기업 리스트를 조회합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT corp_name FROM {TABLE_NAME}")
        result = cursor.fetchall()
        return result
    except mysql.connector.Error as err:
        print(f"Corp list retrieval failed: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_year_list(corp_name):
    """연도 목록을 조회합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT year FROM {TABLE_NAME} WHERE corp_name = %s order by year desc", (corp_name,))
        result = cursor.fetchall()
        return result
    except mysql.connector.Error as err:
        print(f"Year list retrieval failed: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_jasan_data(corp_name):
    """자산 데이터를 조회합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""
                        SELECT year, amount FROM {TABLE_NAME} WHERE corp_name = %s AND account_nm = '자산총계'
                        ORDER BY year
                        """, (corp_name,))
        result = cursor.fetchall()
        return result
    except mysql.connector.Error as err:
        print(f"Jasan data retrieval failed: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_account_data_by_year(corp_name, year):
    """특정 기업의 특정 연도 계정과목 데이터를 조회합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT account_id, account_nm, amount FROM {TABLE_NAME}
            WHERE corp_name = %s AND year = %s
        """, (corp_name, year))
        result = cursor.fetchall()
        return result
    except mysql.connector.Error as err:
        print(f"Account data retrieval failed: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_data():
    """모든 기업의 전체 기간 재무상태표를 조회합니다."""
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""
                        SELECT corp_name, account_id, account_nm, amount, year FROM {TABLE_NAME}
                        ORDER BY corp_name, year
                        """)
        result = cursor.fetchall()
        return result
    except mysql.connector.Error as err:
        print(f"All data retrieval failed: {err}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 수현 추가 = DB 조회용 함수
def get_data_for_compare(corp_name, year):
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)  # dict 형태로 받기
        
        cursor.execute(f"""
            SELECT account_id, account_nm, amount 
            FROM {TABLE_NAME}
            WHERE corp_name = %s AND year = %s
        """, (corp_name, year))

        return cursor.fetchall()
    except:
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_pie_data(corp_name, year):
    """
    파이 차트용 자본총계와 부채총계 데이터를 조회합니다.
    
    Args:
        corp_name (str): 기업 이름
        year (str): 연도
        
    Returns:
        dict: {'자본총계': amount, '부채총계': amount} 형식의 딕셔너리
    """
    conn = None
    cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT account_nm, amount FROM {TABLE_NAME}
            WHERE corp_name = %s AND year = %s AND account_nm IN ('자본총계', '부채총계')
        """, (corp_name, year))
        
        rows = cursor.fetchall()
        data = {row[0]: row[1] for row in rows}
        return data
    except mysql.connector.Error as err:
        print(f"Pie data retrieval failed: {err}")
        return {}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()