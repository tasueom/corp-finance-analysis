"""
재무 데이터 처리 서비스 모듈
데이터베이스 삽입, 내보내기, 비교, 재무지표 계산 등 담당
"""
import pandas as pd
import math
from app import db
from app.api_service import get_finance_dataframe_10years


def prepare_data_for_insert(corp_name):
    """
    기업 이름을 받아서 데이터베이스 삽입을 위한 데이터를 준비합니다.
    
    Args:
        corp_name (str): 기업 이름
        
    Returns:
        tuple: (success: bool, message: str, insert_values: list, is_update: bool)
    """
    if not corp_name:
        return False, '기업 이름이 필요합니다.', None, False
    
    try:
        df = get_finance_dataframe_10years(corp_name)
        
        if df.empty:
            return False, '저장할 데이터가 없습니다.', None, False
        
        corp_code = df.iloc[0]['corp_code'] if not df.empty else None
        if not corp_code:
            return False, '기업 코드를 찾을 수 없습니다.', None, False
        
        latest_year_to_insert = int(df['year'].max())
        db_latest_year = db.get_latest_year_by_corp_code(corp_code)
        
        if db_latest_year is not None and db_latest_year == latest_year_to_insert:
            return False, '이미 데이터가 등록된 기업입니다.', None, False
        
        is_update = False
        if db_latest_year is not None and db_latest_year != latest_year_to_insert:
            delete_success = db.delete_data_by_corp_code(corp_code)
            if not delete_success:
                return False, '기존 데이터 삭제 중 오류가 발생했습니다.', None, False
            is_update = True
        
        insert_values = []
        for row in df.to_dict('records'):
            amount = row.get('amount')
            year = row.get('year')
            
            if amount is None or (isinstance(amount, float) and math.isnan(amount)):
                amount_value = None
            else:
                try:
                    amount_value = int(float(amount))
                except (ValueError, TypeError):
                    amount_value = None
            
            if year is None or (isinstance(year, float) and math.isnan(year)):
                year_value = None
            else:
                try:
                    year_value = int(float(year))
                except (ValueError, TypeError):
                    year_value = None
            
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
    """데이터베이스의 모든 데이터를 CSV 형식으로 내보냅니다."""
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
    """데이터베이스의 모든 데이터를 JSON 형식으로 내보냅니다."""
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


def get_amount_by_account_id(rows, account_id):
    """account_id로 금액을 조회하는 헬퍼 함수"""
    if account_id is None:
        return None
    for row in rows:
        if row[0] == account_id:
            return row[2]
    return None


def find_account_id_by_name(rows, account_name):
    """계정명으로 account_id를 찾는 헬퍼 함수"""
    for row in rows:
        if row[1] == account_name:
            return row[0]
    return None


def calculate_financial_indicators(rows):
    """
    재무지표를 계산합니다.
    
    Args:
        rows: 계정 데이터 리스트 [(account_id, account_nm, amount), ...]
        
    Returns:
        dict: 재무지표 딕셔너리
    """
    if not rows:
        return {
            'current_ratio': None,
            'debt_ratio': None,
            'equity_ratio': None,
            'quick_ratio': None,
            'debt_to_equity': None
        }
    
    account_ids = {
        '유동자산': find_account_id_by_name(rows, '유동자산'),
        '유동부채': find_account_id_by_name(rows, '유동부채'),
        '부채총계': find_account_id_by_name(rows, '부채총계'),
        '자본총계': find_account_id_by_name(rows, '자본총계'),
        '자산총계': find_account_id_by_name(rows, '자산총계'),
        '재고자산': find_account_id_by_name(rows, '재고자산')
    }
    
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


def make_compare_table(compare_list):
    """비교 테이블 생성 함수"""
    dfs = []

    for item in compare_list:
        corp = item["corp"]
        year = item["year"]

        rows = db.get_data_for_compare(corp, year)
        df = pd.DataFrame(rows)

        if df.empty:
            continue

        df = df[["account_id", "account_nm", "amount"]].copy()
        df["amount"] = df["amount"].apply(
            lambda x: None if x in [0, 0.0, "0", "0.0"] else x
        )
        df = df.rename(columns={"amount": f"{corp}({year})"})

        dfs.append(df)

    if not dfs:
        return None

    result = dfs[0]

    for df in dfs[1:]:
        left_has_id = result["account_id"].notna().any()
        right_has_id = df["account_id"].notna().any()

        if left_has_id and right_has_id:
            merged = pd.merge(result, df, on="account_id", how="outer", suffixes=("_l", "_r"))
            merged["account_nm"] = merged["account_nm_l"].combine_first(merged["account_nm_r"])
            merged = merged.drop(columns=["account_nm_l", "account_nm_r"])
        else:
            merged = pd.merge(result, df, on="account_nm", how="outer")

        result = merged

    value_cols = [col for col in result.columns if "(" in col and ")" in col]

    result["notnull_count"] = result[value_cols].notna().sum(axis=1)
    result = result[result["notnull_count"] >= 2].copy()
    result = result.drop(columns=["notnull_count"])

    final_cols = ["account_nm"] + value_cols

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

    return result[final_cols]


def make_chart_data(compare_list):
    """차트용 데이터 생성"""
    dfs = []

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

    result = dfs[0]
    for df in dfs[1:]:
        result = pd.merge(result, df, on="account_nm", how="outer")

    result = result.fillna(0)

    chart_data = {
        "accounts": result["account_nm"].tolist()
    }

    value_cols = [col for col in result.columns if col != "account_nm"]
    for col in value_cols:
        chart_data[col] = result[col].tolist()

    return chart_data


def prepare_view_data(corp_name, selected_year, years):
    """
    view 페이지용 데이터 준비
    
    Args:
        corp_name: 기업 이름
        selected_year: 선택된 연도
        years: 연도 리스트
    
    Returns:
        tuple: (selected_year: str, rows: list)
    """
    from app.utils import get_latest_year_from_years
    
    if not selected_year and years:
        selected_year = get_latest_year_from_years(years)
    
    if selected_year:
        rows = db.get_account_data_by_year(corp_name, selected_year)
    else:
        rows = []
    
    return selected_year, rows

