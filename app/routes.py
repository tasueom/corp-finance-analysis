from flask import render_template, request, redirect, url_for, session, jsonify, flash, send_file
from app import app, service, db
from io import BytesIO
from app.service import format_korean_number
import easyocr
import os
import cv2
import base64
import numpy as np
from PIL import Image

app.jinja_env.filters["krnum"] = format_korean_number

@app.route('/')
def index():
    readme_content = service.read_readme()
    return render_template('index.html', readme_content=readme_content)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        # 기업 선택 후 재무제표 조회
        corp_name = request.form.get('corp_name')
        if corp_name:
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
                return render_template('search.html', error=str(e), corp_name=corp_name)
    
    return render_template('search.html')

@app.route('/api/search_corps', methods=['GET'])
def api_search_corps():
    """검색어로 기업 목록을 반환하는 API"""
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return jsonify({'corps': []})
    
    try:
        corps = service.search_corps(search_term, limit=50)
        return jsonify({'corps': corps})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/insert_data', methods=['POST'])
def insert_data():
    """데이터베이스에 재무제표 데이터를 삽입합니다."""
    try:
        # POST 요청에서 기업 이름 가져오기
        corp_name = request.form.get('corp_name')
        
        if not corp_name:
            flash('기업 이름이 필요합니다.', 'error')
            return redirect(url_for('search'))
        
        # service에서 데이터 준비
        success, message, insert_values, is_update = service.prepare_data_for_insert(corp_name)
        
        if not success:
            flash(message, 'error' if '오류' in message else 'info')
            return redirect(url_for('search'))
        
        # 데이터베이스에 삽입
        insert_success = db.insert_data(insert_values)
        
        if insert_success:
            if is_update:
                # 갱신된 경우
                flash(f'{corp_name}의 재무제표 데이터가 갱신되었습니다.', 'success')
            else:
                # 새로 삽입된 경우
                flash(f'{corp_name}의 재무제표 데이터 {len(insert_values)}개가 성공적으로 저장되었습니다.', 'success')
        else:
            flash('데이터 저장 중 오류가 발생했습니다.', 'error')
        
        # 검색 결과 페이지로 리다이렉트
        return redirect(url_for('search'))
    
    except Exception as e:
        flash(f'데이터 저장 중 오류가 발생했습니다: {str(e)}', 'error')
        return redirect(url_for('search'))

@app.route('/view', methods=['GET', 'POST'])
def view():
    corp_list = db.get_corp_list()              # 기업 리스트 가져오기
    years = []
    rows = []
    
    # POST 요청에서 선택값 가져오기
    if request.method == "POST":
        action = request.form.get("action")

        # 1) 기업 선택 → 연도 목록 표시 및 최근 연도 자동 선택
        if action == "select_corp":
            selected_corp = request.form.get("corp_name")
            years = db.get_year_list(selected_corp)
            # 최근 연도 자동 선택 (내림차순 정렬되어 있으므로 첫 번째가 최근 연도)
            if years:
                selected_year = str(years[0][0])  # 최근 연도 자동 선택
                rows = db.get_account_data_by_year(selected_corp, selected_year)
            else:
                selected_year = None
                rows = []

        # 2) 연도 선택 → 데이터 조회
        elif action == "select_year":
            selected_corp = request.form.get("corp_name")
            selected_year = request.form.get("year")

            years = db.get_year_list(selected_corp)                  # 연도 다시 로딩 (유지)
            rows = db.get_account_data_by_year(selected_corp, selected_year)
        else:
            selected_corp = None
            selected_year = None
    else:
        # GET 요청 시 쿼리 파라미터에서 가져오기
        selected_corp = request.args.get("corp_name")
        selected_year = request.args.get("year")
        
        if selected_corp:
            years = db.get_year_list(selected_corp)
            # 연도가 선택되지 않았으면 최근 연도 자동 선택
            if not selected_year and years:
                selected_year = str(years[0][0])  # 최근 연도 자동 선택
            if selected_year:
                rows = db.get_account_data_by_year(selected_corp, selected_year)
        else:
            selected_corp = None
            selected_year = None

    return render_template(
        "view.html",
        corp_list=corp_list,
        years=years,
        rows=rows,
        selected_corp=selected_corp,
        selected_year=selected_year
    )

@app.route('/chart', methods=['GET', 'POST'])
def chart():
    corp_list = [row[0] for row in db.get_corp_list()]
    
    selected_corp = request.form.get('corp')
    selected_year = request.form.get('year')
    year_list = []
    
    if selected_corp:
        year_list = [row[0] for row in db.get_year_list(selected_corp)]
        # 연도가 선택되지 않았으면 최근 연도 자동 선택
        if not selected_year and year_list:
            selected_year = str(year_list[0])  # 최근 연도 자동 선택
    
    return render_template('chart.html',
                            corp_list=corp_list,
                            selected_corp=selected_corp,
                            year_list=year_list,
                            selected_year=selected_year)

@app.route('/chart1_data/<corp>')
def chart1_data(corp):
    data = db.get_jasan_data(corp)
    years = [row[0] for row in data]
    amounts = [row[1] for row in data]
    return jsonify({'years': years, 'amounts': amounts})

@app.route('/chart2_data/<corp>/<year>')
def chart2_data(corp, year):
    data = db.get_account_data_by_year(corp, year)
    # row[0]: account_id (로직용), row[1]: account_nm (표시용), row[2]: amount
    accounts = [row[1] for row in data]  # account_nm만 표시
    amounts = [row[2] for row in data]   # amount
    return jsonify({'accounts': accounts, 'amounts': amounts})

@app.route("/export_csv")
def export_csv():
    df = service.export_data_to_csv()
    
    # BytesIO를 사용하여 가상 파일 생성
    output = BytesIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)  # 파일 포인터를 처음으로 이동
    
    return send_file(
        output,
        as_attachment=True,
        download_name="재무상태표.csv",
        mimetype="text/csv"
    )
    
@app.route("/export_json")
def export_json():
    json_str = service.export_data_to_json()
    
    # BytesIO를 사용하여 가상 파일 생성
    output = BytesIO()
    output.write(json_str.encode('utf-8'))
    output.seek(0)  # 파일 포인터를 처음으로 이동
    
    return send_file(
        output,
        as_attachment=True,
        download_name="재무상태표.json",
        mimetype="application/json"
    )

@app.route("/predict", methods=['GET', 'POST'])
def predict():
    """머신러닝 모델을 사용한 재무 지표 예측"""
    from datetime import datetime
    
    corp_list = [row[0] for row in db.get_corp_list()]
    selected_corp = request.form.get('corp') if request.method == 'POST' else request.args.get('corp')
    selected_year = request.form.get('year') if request.method == 'POST' else request.args.get('year')
    prediction_result = None
    predicted_year = None
    metrics = None
    avg_metrics = None
    
    # 최소 연도 계산 (시스템 날짜의 내년도)
    current_year = datetime.now().year
    min_year = current_year + 1
    
    # 예측하기 버튼이 눌렸을 때만 연도 검사 및 예측 수행
    predict_btn = request.form.get('predict_btn')
    
    if selected_corp and predict_btn == 'predict':
        # 예측하기 버튼을 눌렀을 때만 연도 검사
        if not selected_year:
            flash('예측 연도를 입력해주세요.', 'error')
        else:
            try:
                # 연도 유효성 검사
                year_int = int(selected_year)
                if year_int < min_year:
                    flash(f'예측 연도는 {min_year}년 이상이어야 합니다.', 'error')
                else:
                    # 데이터 준비
                    pivot, target_df = service.scikit()
                    
                    # 모델 학습 (성능 지표 포함)
                    model, COMMON_IDS, TARGET_IDS, metrics, avg_metrics = service.train_model(pivot, target_df)
                    
                    # 예측 수행 (연도 전달)
                    prediction_result = service.predict_company(model, pivot, selected_corp, COMMON_IDS, TARGET_IDS, target_year=year_int)
                    predicted_year = year_int
                    
            except ValueError as e:
                # 숫자가 아닌 경우 또는 다른 ValueError
                if 'invalid literal' in str(e) or 'could not convert' in str(e):
                    flash('올바른 연도를 입력해주세요.', 'error')
                else:
                    flash(str(e), 'error')
            except Exception as e:
                flash(f'예측 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return render_template('predict.html',
                          corp_list=corp_list,
                          selected_corp=selected_corp,
                          selected_year=selected_year,
                          min_year=min_year,
                          prediction_result=prediction_result,
                          predicted_year=predicted_year,
                          metrics=metrics,
                          avg_metrics=avg_metrics)

# 수현추가 = 비교 기능 추가
@app.route('/compare', methods=['GET', 'POST'])
def compare():
    corp_list = db.get_corp_list()

    if request.method == "POST":
        # 여러 비교 대상 받아오기
        corp_names = request.form.getlist("corp_name")
        years = request.form.getlist("year")

        compare_list = []

        for corp, yr in zip(corp_names, years):
            if corp and yr:
                compare_list.append({"corp": corp, "year": yr})

        if len(compare_list) < 2:
            return render_template(
                "compare.html",
                corp_list=corp_list,
                error="최소 2개 이상의 비교 대상을 선택하세요."
            )

        # 비교 테이블 생성
        result_df = service.make_compare_table(compare_list)
        
        # 🔥 여기서 차트용 데이터 생성
        chart_data = service.make_chart_data(compare_list)

        if result_df is None or result_df.empty:
            return render_template(
                "compare.html",
                corp_list=corp_list,
                error="비교 가능한 항목이 없습니다."
            )

        return render_template(
            "compare.html",
            corp_list=corp_list,
            columns=result_df.columns,
            result=result_df.to_dict("records"),
            chart_data=chart_data
        )

    return render_template("compare.html", corp_list=corp_list)


# 수현추가 = 연도 리스트 API
@app.route('/api/get_years')
def api_get_years():
    corp = request.args.get('corp')
    years = db.get_year_list(corp)
    years = [y[0] for y in years]
    return jsonify({'years': years})

# ================================
# 수현: 명함 OCR 라우터
# ================================
reader = easyocr.Reader(['ko', 'en'], gpu=False)

@app.route('/ocr', methods=['GET', 'POST'])
def ocr():
    image_base64 = None
    text_lines = None

    if request.method == 'POST':
        file = request.files['image']
        if not file:
            return render_template('ocr.html', error="파일이 없습니다.")

        # 파일을 BytesIO로 읽기
        image_bytes = BytesIO()
        file.save(image_bytes)
        image_bytes.seek(0)
        
        # 이미지를 base64로 인코딩 (화면 표시용)
        import base64
        image_base64 = base64.b64encode(image_bytes.read()).decode('utf-8')
        image_bytes.seek(0)
        
        # 이미지 형식 확인
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
        mime_type = f'image/{file_ext}' if file_ext in ['jpg', 'jpeg', 'png', 'gif'] else 'image/png'
        image_data_uri = f'data:{mime_type};base64,{image_base64}'
        
        # OCR 실행을 위해 numpy 배열로 변환
        import numpy as np
        from PIL import Image
        img = Image.open(image_bytes)
        img_array = np.array(img)
        
        # easyocr 실행 (numpy 배열 사용)
        text_lines = reader.readtext(img_array, detail=0)

    return render_template(
        'ocr.html',
        image_data_uri=image_data_uri if image_base64 else None,
        text_lines=text_lines
    )
