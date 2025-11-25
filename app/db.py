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

TABLE_NAME = "corp_finance"

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
        cursor.executemany(f"INSERT INTO {TABLE_NAME} (corp_name, corp_code, account_nm, amount, year) VALUES (%s, %s, %s, %s, %s)", data)
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