from flask import render_template, request, redirect, url_for, session, jsonify, flash, send_file
from app import app, service, db
from io import BytesIO

@app.route('/')
def index():
    readme_content = service.read_readme()
    return render_template('index.html', readme_content=readme_content)

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
    accounts = [row[0] for row in data]
    amounts = [row[1] for row in data]
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