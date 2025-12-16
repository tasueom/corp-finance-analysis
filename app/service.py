"""
통합 서비스 모듈
모든 서비스를 import하여 기존 코드와의 호환성 유지
"""
# 모든 서비스를 import
from app.api_service import (
    load_corp_code_cache,
    get_corp_code,
    search_corps,
    get_finance_data,
    get_finance_dataframe,
    get_finance_dataframe_10years
)

from app.finance_service import (
    prepare_data_for_insert,
    export_data_to_csv,
    export_data_to_json,
    calculate_financial_indicators,
    make_compare_table,
    make_chart_data,
    get_amount_by_account_id,
    find_account_id_by_name,
    prepare_view_data
)

from app.utils import (
    read_readme,
    format_korean_number,
    validate_year,
    get_latest_year_from_years,
    check_duplicate_compare_items
)

# ML 서비스는 지연 로딩 (무거운 라이브러리)
def scikit():
    from app.ml_service import scikit
    return scikit()

def train_model(pivot, target_df):
    from app.ml_service import train_model
    return train_model(pivot, target_df)

def predict_company(model, pivot, corp_name, COMMON_IDS, TARGET_IDS, target_year=None):
    from app.ml_service import predict_company
    return predict_company(model, pivot, corp_name, COMMON_IDS, TARGET_IDS, target_year)

# PDF 서비스는 지연 로딩
def generate_pdf_chart_image(rows, selected_corp, selected_year):
    from app.pdf_service import generate_pdf_chart_image
    return generate_pdf_chart_image(rows, selected_corp, selected_year)

def generate_pdf_document(rows, selected_corp, selected_year, chart_image_buffer):
    from app.pdf_service import generate_pdf_document
    return generate_pdf_document(rows, selected_corp, selected_year, chart_image_buffer)
