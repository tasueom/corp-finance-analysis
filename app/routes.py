from flask import render_template, request, redirect, url_for, session
from app import app, service

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        corp_name = request.form['corp_name']
        corp_code = service.get_corp_code(corp_name)
        return redirect(url_for('search.html', corp_name=corp_name, corp_code=corp_code))
    return render_template('search.html')