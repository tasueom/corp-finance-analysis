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

DB_NAME = os.environ.get('DB_NAME', 'scoredb')

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