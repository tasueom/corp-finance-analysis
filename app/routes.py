from flask import render_template, request, redirect, url_for, session, jsonify, flash
from app import app, service, db
import pandas as pd

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        corp_name = request.form['corp_name']
        try:
            # 10년치 DataFrame 가져오기
            df = service.get_finance_dataframe_10years(corp_name)
            
            # DataFrame을 딕셔너리 리스트로 변환하여 템플릿에 전달
            data = df.to_dict('records')
            columns = df.columns.tolist()
            
            return render_template('search.html', 
                                    corp_name=corp_name,
                                    data=data,
                                    columns=columns,
                                    row_count=len(data))
        except Exception as e:
            return render_template('search.html', error=str(e), corp_name=corp_name if 'corp_name' in locals() else '')
    
    return render_template('search.html')

@app.route('/insert_data', methods=['POST'])
def insert_data():
    """데이터베이스에 재무제표 데이터를 삽입합니다."""
    try:
        # POST 요청에서 기업 이름 가져오기
        corp_name = request.form.get('corp_name')
        
        if not corp_name:
            flash('기업 이름이 필요합니다.', 'error')
            return redirect(url_for('search'))
        
        # 기업 이름으로 다시 데이터 조회
        df = service.get_finance_dataframe_10years(corp_name)
        
        # DataFrame을 튜플 리스트로 변환 (db.insert_data에 맞는 형식)
        # 컬럼 순서: corp_name, corp_code, account_nm, amount, year
        import math
        
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
            
            insert_values.append((
                row.get('corp_name', ''),
                row.get('corp_code', ''),
                row.get('account_nm', ''),
                amount_value,
                year_value
            ))
        
        # 데이터베이스에 삽입
        success = db.insert_data(insert_values)
        
        if success:
            flash(f'{corp_name}의 재무제표 데이터 {len(insert_values)}개가 성공적으로 저장되었습니다.', 'success')
        else:
            flash('데이터 저장 중 오류가 발생했습니다.', 'error')
        
        # 검색 결과 페이지로 리다이렉트
        return redirect(url_for('search'))
    
    except Exception as e:
        flash(f'데이터 저장 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('search'))