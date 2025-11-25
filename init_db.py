from app.db import create_database, drop_table, create_table

if __name__ == '__main__':
    print("데이터베이스 생성 중...")
    if create_database():
        print("✓ 데이터베이스 생성 완료")
    else:
        print("✗ 데이터베이스 생성 실패")
    
    print("\n기존 테이블 삭제 중...")
    if drop_table():
        print("✓ 테이블 삭제 완료")
    else:
        print("✗ 테이블 삭제 실패 (테이블이 존재하지 않을 수 있습니다)")
    
    print("\n테이블 생성 중...")
    if create_table():
        print("✓ 테이블 생성 완료")
    else:
        print("✗ 테이블 생성 실패")
