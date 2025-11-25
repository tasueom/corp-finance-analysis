from flask import render_template, request, redirect, url_for, session, jsonify
from app import app, service
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

@app.route('/finance-data', methods=['GET', 'POST'])
def finance_data():
    """
    기업 이름을 받아서 재무제표 데이터를 DataFrame으로 반환합니다.
    GET 또는 POST 요청으로 corp_name 파라미터를 받습니다.
    """
    if request.method == 'POST':
        corp_name = request.form.get('corp_name')
    else:
        corp_name = request.args.get('corp_name')
    
    if not corp_name:
        return jsonify({'error': '기업 이름(corp_name)이 필요합니다.'}), 400
    
    try:
        # DataFrame 가져오기
        df = service.get_finance_dataframe(corp_name)
        
        # DataFrame을 JSON으로 변환하여 반환
        # to_dict('records')는 각 행을 딕셔너리로 변환
        return jsonify({
            'success': True,
            'data': df.to_dict('records'),
            'shape': df.shape,
            'columns': df.columns.tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500