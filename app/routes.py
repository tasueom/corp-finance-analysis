from flask import render_template, request, redirect, url_for, session, jsonify, flash, send_file
from app import app, service, db
from io import BytesIO
from datetime import datetime

app.jinja_env.filters["krnum"] = service.format_korean_number

@app.route('/')
def index():
    service.send_event_to_ga4('page_view', {'page_location': url_for('index', _external=True), 'page_title': 'Index'})
    readme_content = service.read_readme()
    return render_template('index.html', readme_content=readme_content)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        corp_name = request.form.get('corp_name')
        if corp_name:
            service.send_event_to_ga4('search', {'search_term': corp_name})
            try:
                df = service.get_finance_dataframe_10years(corp_name)
                data = df.to_dict('records')
                columns = df.columns.tolist()
                
                return render_template('search.html', 
                                        corp_name=corp_name,
                                        data=data,
                                        columns=columns,
                                        row_count=len(data))
            except Exception as e:
                return render_template('search.html', error=str(e), corp_name=corp_name)
    else:
        service.send_event_to_ga4('page_view', {'page_location': url_for('search', _external=True), 'page_title': 'Search'})
    
    return render_template('search.html')

@app.route('/api/search_corps', methods=['GET'])
def api_search_corps():
    """검색어로 기업 목록을 반환하는 API"""
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return jsonify({'corps': []})
    
    service.send_event_to_ga4('api_search_corps', {'search_term': search_term})
    try:
        corps = service.search_corps(search_term, limit=50)
        return jsonify({'corps': corps})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/insert_data', methods=['POST'])
def insert_data():
    """데이터베이스에 재무제표 데이터를 삽입합니다."""
    corp_name = None
    try:
        # POST 요청에서 기업 이름 가져오기
        corp_name = request.form.get('corp_name')
        
        if not corp_name:
            flash('기업 이름이 필요합니다.', 'error')
            return redirect(url_for('search'))
        
        service.send_event_to_ga4('db_insert_attempt', {'corp_name': corp_name})
        
        # service에서 데이터 준비
        success, message, insert_values, is_update = service.prepare_data_for_insert(corp_name)
        
        if not success:
            flash(message, 'error' if '오류' in message else 'info')
            return redirect(url_for('search'))
        
        # 데이터베이스에 삽입
        insert_success = db.insert_data(insert_values)
        
        if insert_success:
            event_name = 'db_update_data' if is_update else 'db_insert_new_data'
            service.send_event_to_ga4(event_name, {'corp_name': corp_name})
            if is_update:
                flash(f'{corp_name}의 재무제표 데이터가 갱신되었습니다.', 'success')
            else:
                flash(f'{corp_name}의 재무제표 데이터 {len(insert_values)}개가 성공적으로 저장되었습니다.', 'success')
        else:
            flash('데이터 저장 중 오류가 발생했습니다.', 'error')
        
        return redirect(url_for('search'))
    
    except Exception as e:
        flash(f'데이터 저장 중 오류가 발생했습니다: {str(e)}', 'error')
        if corp_name:
            service.send_event_to_ga4('error', {'error_type': 'insert_data_failed', 'corp_name': corp_name})
        return redirect(url_for('search'))

@app.route('/view', methods=['GET', 'POST'])
def view():
    corp_list = db.get_corp_list()
    years = []
    rows = []
    indicators = None
    
    if request.method == "POST":
        action = request.form.get("action")

        if action == "select_corp":
            selected_corp = request.form.get("corp_name")
            service.send_event_to_ga4('select_corp_view', {'corp_name': selected_corp})
            years = db.get_year_list(selected_corp)
            selected_year, rows = service.prepare_view_data(selected_corp, None, years)

        elif action == "select_year":
            selected_corp = request.form.get("corp_name")
            selected_year = request.form.get("year")
            service.send_event_to_ga4('select_year_view', {'corp_name': selected_corp, 'year': selected_year})
            years = db.get_year_list(selected_corp)
            selected_year, rows = service.prepare_view_data(selected_corp, selected_year, years)
        else:
            selected_corp = None
            selected_year = None
    else:
        service.send_event_to_ga4('page_view', {'page_location': url_for('view', _external=True), 'page_title': 'Data View'})
        selected_corp = request.args.get("corp_name")
        selected_year = request.args.get("year")
        
        if selected_corp:
            service.send_event_to_ga4('view_by_get', {'corp_name': selected_corp, 'year': selected_year or 'Latest'})
            years = db.get_year_list(selected_corp)
            selected_year, rows = service.prepare_view_data(selected_corp, selected_year, years)
        else:
            selected_corp = None
            selected_year = None
    
    indicators = service.calculate_financial_indicators(rows) if rows else None

    return render_template(
        "view.html",
        corp_list=corp_list,
        years=years,
        rows=rows,
        selected_corp=selected_corp,
        selected_year=selected_year,
        indicators=indicators
    )

@app.route('/chart', methods=['GET', 'POST'])
def chart():
    corp_list = [row[0] for row in db.get_corp_list()]
    
    selected_corp = request.form.get('corp')
    selected_year = request.form.get('year')
    year_list = []
    
    if request.method == 'POST':
        service.send_event_to_ga4('select_corp_chart', {'corp_name': selected_corp, 'year': selected_year or 'Default Year'})
    else:
        service.send_event_to_ga4('page_view', {'page_location': url_for('chart', _external=True), 'page_title': 'Chart'})
        
    if selected_corp:
        years = db.get_year_list(selected_corp)
        year_list = [row[0] for row in years]
        if not selected_year and years:
            selected_year = service.get_latest_year_from_years(years)
    
    return render_template('chart.html',
                            corp_list=corp_list,
                            selected_corp=selected_corp,
                            year_list=year_list,
                            selected_year=selected_year)

@app.route('/chart1_data/<corp>')
def chart1_data(corp):
    service.send_event_to_ga4('api_get_chart1', {'corp_name': corp})
    data = db.get_jasan_data(corp)
    years = [row[0] for row in data]
    amounts = [row[1] for row in data]
    return jsonify({'years': years, 'amounts': amounts})

@app.route('/chart2_data/<corp>/<year>')
def chart2_data(corp, year):
    service.send_event_to_ga4('api_get_chart2', {'corp_name': corp, 'year': year})
    data = db.get_account_data_by_year(corp, year)
    accounts = [row[1] for row in data]
    amounts = [row[2] for row in data]
    return jsonify({'accounts': accounts, 'amounts': amounts})

@app.route("/export_csv")
def export_csv():
    service.send_event_to_ga4('export', {'format': 'csv'})
    df = service.export_data_to_csv()
    
    output = BytesIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name="재무상태표.csv",
        mimetype="text/csv"
    )
    
@app.route("/export_json")
def export_json():
    service.send_event_to_ga4('export', {'format': 'json'})
    json_str = service.export_data_to_json()
    
    output = BytesIO()
    output.write(json_str.encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name="재무상태표.json",
        mimetype="application/json"
    )

@app.route("/export_pdf", methods=["GET"])
def export_pdf():
    selected_corp = request.args.get("corp_name")
    selected_year = request.args.get("year")
    
    if not selected_corp:
        flash("기업을 선택해주세요.", "error")
        return redirect(url_for("view", corp_name=selected_corp, year=selected_year))
    
    service.send_event_to_ga4('export_attempt', {'format': 'pdf', 'corp_name': selected_corp, 'year': selected_year or 'Latest'})
    
    years = db.get_year_list(selected_corp)
    if not selected_year and years:
        selected_year = service.get_latest_year_from_years(years)
        
    if selected_year:
        rows = db.get_account_data_by_year(selected_corp, selected_year)
    else:
        rows = []

    if not rows:
        flash("해당 연도의 데이터가 존재하지 않습니다.", "error")
        return redirect(url_for("view"))
    
    chart_image_buffer = service.generate_pdf_chart_image(rows, selected_corp, selected_year)
    pdf_buffer = service.generate_pdf_document(rows, selected_corp, selected_year, chart_image_buffer)
    
    filename = f"{selected_corp}_{selected_year}_재무상태표.pdf"
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

@app.route("/predict", methods=['GET', 'POST'])
def predict():
    """머신러닝 모델을 사용한 재무 지표 예측"""
    corp_list = [row[0] for row in db.get_corp_list()]
    selected_corp = request.form.get('corp') if request.method == 'POST' else request.args.get('corp')
    selected_year = request.form.get('year') if request.method == 'POST' else request.args.get('year')
    prediction_result = None
    predicted_year = None
    metrics = None
    avg_metrics = None
    
    current_year = datetime.now().year
    min_year = current_year + 1
    
    predict_btn = request.form.get('predict_btn')
    
    if request.method == 'GET':
        service.send_event_to_ga4('page_view', {'page_location': url_for('predict', _external=True), 'page_title': 'Prediction'})
    
    if selected_corp and predict_btn == 'predict':
        service.send_event_to_ga4('prediction_attempt', {'corp_name': selected_corp, 'year': selected_year})
        if not selected_year:
            flash('예측 연도를 입력해주세요.', 'error')
        else:
            try:
                is_valid, year_int, error_msg = service.validate_prediction_year(selected_year, min_year)
                if not is_valid:
                    flash(error_msg, 'error')
                else:
                    pivot, target_df = service.scikit()
                    model, COMMON_IDS, TARGET_IDS, metrics, avg_metrics = service.train_model(pivot, target_df)
                    prediction_result = service.predict_company(model, pivot, selected_corp, COMMON_IDS, TARGET_IDS, target_year=year_int)
                    predicted_year = year_int
                    service.send_event_to_ga4('prediction_success', {'corp_name': selected_corp, 'year': year_int})
                    
            except ValueError as e:
                if 'invalid literal' in str(e) or 'could not convert' in str(e):
                    flash('올바른 연도를 입력해주세요.', 'error')
                else:
                    flash(str(e), 'error')
            except Exception as e:
                flash(f'예측 중 오류가 발생했습니다: {str(e)}', 'error')
                service.send_event_to_ga4('error', {'error_type': 'prediction_failed', 'corp_name': selected_corp, 'year': selected_year})
    
    return render_template('predict.html',
                          corp_list=corp_list,
                          selected_corp=selected_corp,
                          selected_year=selected_year,
                          min_year=min_year,
                          prediction_result=prediction_result,
                          predicted_year=predicted_year,
                          metrics=metrics,
                          avg_metrics=avg_metrics)

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    """기업 비교 기능"""
    corp_list = db.get_corp_list()

    if request.method == "POST":
        corp_names = request.form.getlist("corp_name")
        years = request.form.getlist("year")

        compare_list = []

        for corp, yr in zip(corp_names, years):
            if corp and yr:
                compare_list.append({"corp": corp, "year": yr})

        if len(compare_list) < 2:
            flash("최소 2개 이상의 비교 대상을 선택하세요.", "error")
            return render_template("compare.html", corp_list=corp_list)
        
        compare_list, duplicates = service.check_duplicate_compare_items(compare_list)
        
        if duplicates:
            flash(f"동일한 옵션이 중복 선택되었습니다: {', '.join(duplicates)}", "warning")
            
            if len(compare_list) < 2:
                flash("중복 제거 후 비교 대상이 부족합니다. 최소 2개 이상의 비교 대상을 선택하세요.", "error")
                return render_template("compare.html", corp_list=corp_list, error="최소 2개 이상의 비교 대상을 선택하세요.")
        
        service.send_event_to_ga4('submit_comparison', {'item_count': len(compare_list)})

        result_df = service.make_compare_table(compare_list)
        chart_data = service.make_chart_data(compare_list)

        if result_df is None or result_df.empty:
            return render_template("compare.html", corp_list=corp_list, error="비교 가능한 항목이 없습니다.")

        return render_template(
            "compare.html",
            corp_list=corp_list,
            columns=result_df.columns,
            result=result_df.to_dict("records"),
            chart_data=chart_data
        )

    service.send_event_to_ga4('page_view', {'page_location': url_for('compare', _external=True), 'page_title': 'Compare'})
    return render_template("compare.html", corp_list=corp_list)

@app.route('/api/get_years')
def api_get_years():
    """연도 리스트 API"""
    corp = request.args.get('corp')
    service.send_event_to_ga4('api_get_years', {'corp_name': corp})
    years = db.get_year_list(corp)
    years = [y[0] for y in years]
    return jsonify({'years': years})

@app.route('/pie_data/<corp>/<year>')
def pie_data(corp, year):
    """파이 차트 데이터 API"""
    service.send_event_to_ga4('api_get_pie_data', {'corp_name': corp, 'year': year})
    data = db.get_pie_data(corp, year)
    return jsonify(data)

@app.route('/ocr', methods=['GET', 'POST'])
def ocr():
    """OCR 기능"""
    image_data_uri = None
    text_lines = None

    if request.method == 'POST':
        file = request.files['image']
        if not file:
            return render_template('ocr.html', error="파일이 없습니다.")
        
        service.send_event_to_ga4('perform_ocr', {'filename': file.filename})
        image_data_uri, text_lines = service.process_image(file)
    else:
        service.send_event_to_ga4('page_view', {'page_location': url_for('ocr', _external=True), 'page_title': 'OCR'})

    return render_template(
        'ocr.html',
        image_data_uri=image_data_uri,
        text_lines=text_lines
    )

