# 기업 재무상태표 분석 시스템

DART(Data Analysis, Retrieval and Transfer system) Open API를 활용하여 기업의 재무상태표 데이터를 조회, 저장, 분석 및 시각화하는 웹 애플리케이션입니다.

## 주요 기능

- 🔍 **기업 검색**: 검색어 입력 시 해당 검색어를 포함하는 기업 목록을 표시하고, 선택한 기업의 최근 10년치 재무상태표 데이터 조회
- 💾 **데이터 저장**: 조회한 재무상태표 데이터를 MySQL 데이터베이스에 저장
- 📊 **데이터 조회**: 저장된 기업별, 연도별 재무상태표 데이터 조회
- 📈 **차트 시각화**: 자산총계 추이 및 연도별 계정과목 분포 차트 제공
- 📥 **데이터 내보내기**: CSV, JSON 형식으로 데이터 내보내기

## 기술 스택

- **Backend**: Python 3.x, Flask
- **Database**: MySQL
- **Data Processing**: pandas
- **API**: DART Open API
- **Frontend**: HTML, CSS, JavaScript (Chart.js)

## 프로젝트 구조

```
team2-corp-anal/
├── app/
│   ├── __init__.py          # Flask 앱 초기화
│   ├── routes.py            # 라우팅 및 요청 처리
│   ├── service.py           # 비즈니스 로직 (API 호출, 데이터 처리)
│   ├── db.py                # 데이터베이스 연동
│   ├── templates/           # HTML 템플릿
│   │   ├── layout.html
│   │   ├── index.html
│   │   ├── search.html
│   │   ├── view.html
│   │   └── chart.html
│   └── static/              # 정적 파일
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── chart.js
│           └── search.js
├── app.py                   # 애플리케이션 진입점
├── init_db.py               # 데이터베이스 초기화 스크립트
└── README.md
```

## 설치 및 설정

### 1. 필수 요구사항

- Python 3.7 이상
- MySQL 5.7 이상
- DART Open API 키 ([DART Open API 홈페이지](https://opendart.fss.or.kr/)에서 발급)

### 2. 패키지 설치

```bash
pip install flask
pip install mysql-connector-python
pip install pandas
pip install python-dotenv
pip install requests
```

### 3. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 입력하세요:

```env
# DART API 설정
API_KEY=your_dart_api_key_here
BASE_URL=https://opendart.fss.or.kr/api

# 데이터베이스 설정
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=corpdb
TABLE_NAME=corp_finance

# Flask 설정
SECRET_KEY=your_secret_key_here
```

### 4. 데이터베이스 초기화

```bash
python init_db.py
```

이 스크립트는 다음 작업을 수행합니다:
- 데이터베이스 생성
- 기존 테이블 삭제 (있는 경우)
- 재무상태표 데이터 저장용 테이블 생성

## 실행 방법

```bash
python app.py
```

애플리케이션이 실행되면 브라우저에서 `http://localhost:5000`으로 접속할 수 있습니다.

## 사용 방법

### 1. 기업 검색 및 데이터 조회

1. 메인 페이지에서 "검색" 메뉴로 이동
2. 검색어 입력 (예: "삼성") - 정확한 기업명을 몰라도 검색어만으로 검색 가능
3. 검색 버튼 클릭 또는 Enter 키 입력
4. 검색 결과로 표시된 기업 목록에서 원하는 기업 선택
   - 각 기업은 기업명과 기업 코드가 함께 표시됩니다
   - 검색 결과를 불러오는데 시간이 다소 소요될 수 있습니다
5. 선택한 기업의 최근 10년치 재무상태표 데이터 확인
6. 필요시 "데이터 저장" 버튼으로 데이터베이스에 저장

### 2. 저장된 데이터 조회

1. "조회" 메뉴로 이동
2. 기업 선택
3. 연도 선택 (자동으로 최근 연도가 선택됨)
4. 해당 연도의 계정과목별 금액 확인

### 3. 차트 시각화

1. "차트" 메뉴로 이동
2. 기업 선택
3. 연도 선택
4. 다음 차트 확인:
   - **차트 1**: 자산총계 연도별 추이
   - **차트 2**: 선택한 연도의 계정과목별 금액 분포

### 4. 데이터 내보내기

- "CSV 내보내기": 모든 저장된 데이터를 CSV 파일로 다운로드
- "JSON 내보내기": 모든 저장된 데이터를 JSON 파일로 다운로드

## 라우트 목록

### 웹 페이지 라우트 (HTML 반환)

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/` | GET | 메인 페이지 (README 표시) |
| `/search` | GET, POST | 기업 검색 및 재무상태표 조회 페이지 |
| `/view` | GET, POST | 저장된 데이터 조회 페이지 |
| `/chart` | GET, POST | 차트 시각화 페이지 |
| `/insert_data` | POST | 재무상태표 데이터 저장 (리다이렉트) |

### API 엔드포인트 (JSON/파일 반환)

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/api/search_corps` | GET | 검색어로 기업 목록 조회 (JSON) |
| `/chart1_data/<corp>` | GET | 자산총계 추이 데이터 (JSON) |
| `/chart2_data/<corp>/<year>` | GET | 연도별 계정과목 데이터 (JSON) |
| `/export_csv` | GET | CSV 파일 다운로드 |
| `/export_json` | GET | JSON 파일 다운로드 |

## 데이터 구조

### 재무상태표 데이터 (corp_finance 테이블)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | INT | 기본 키 (자동 증가) |
| corp_name | VARCHAR(100) | 기업 이름 |
| corp_code | VARCHAR(20) | DART 기업 코드 |
| account_nm | VARCHAR(100) | 계정과목명 |
| amount | BIGINT | 금액 |
| year | INT | 연도 |

## 주요 기능 상세

### 기업 검색 기능

- 검색어 입력 시 DART API의 기업 코드 목록에서 해당 검색어를 포함하는 기업을 검색
- 부분 일치 검색 지원: 정확한 기업명을 몰라도 검색어만으로 기업을 찾을 수 있음
- 최대 50개의 검색 결과 표시
- 검색 결과에서 기업명과 기업 코드를 함께 표시하여 정확한 기업 선택 가능

### 재무상태표 데이터 조회

- DART API를 통해 최근 10년치 재무상태표 데이터를 자동으로 조회
- 3년 단위로 효율적으로 데이터 수집 (사업보고서에 당기, 전기, 전전기 데이터 포함)
- 재무상태표(BS) 데이터만 조회하여 데이터량 최적화

### 데이터 저장 로직

- 중복 데이터 체크: 동일 기업의 동일 연도 데이터가 이미 존재하면 저장하지 않음
- 데이터 갱신: 기존 데이터의 최근 연도와 다르면 기존 데이터 삭제 후 새 데이터 저장
- NaN 값 처리: 결측값은 NULL로 저장

## 주의사항

1. **API 키**: DART Open API 키가 필요합니다. 무료로 발급받을 수 있지만 일일 호출 제한이 있을 수 있습니다.
2. **데이터베이스**: MySQL 서버가 실행 중이어야 합니다.
3. **기업 검색**: 검색어만으로도 기업을 찾을 수 있지만, 정확한 기업명을 알고 있으면 더 빠르게 검색할 수 있습니다.
4. **검색 시간**: 기업 목록 검색 시 DART API에서 전체 기업 코드 목록을 다운로드하므로 초기 검색에 시간이 다소 소요될 수 있습니다.
5. **데이터 조회 시간**: 10년치 데이터 조회 시 다소 시간이 걸릴 수 있습니다.

## 문제 해결

### API 키 오류
- `.env` 파일에 올바른 `API_KEY`가 설정되어 있는지 확인
- DART Open API 홈페이지에서 API 키가 활성화되어 있는지 확인

### 데이터베이스 연결 오류
- MySQL 서버가 실행 중인지 확인
- `.env` 파일의 데이터베이스 설정이 올바른지 확인
- 데이터베이스가 생성되었는지 확인 (`init_db.py` 실행)

### 데이터 조회 실패
- 인터넷 연결 확인
- 검색어가 너무 짧거나 일반적인 단어인 경우 많은 결과가 나올 수 있음 (더 구체적인 검색어 사용 권장)
- DART API 일일 호출 제한 확인
- 기업 목록 검색이 느린 경우: DART API에서 전체 기업 코드 목록을 다운로드하므로 첫 검색 시 시간이 걸릴 수 있습니다

## 라이선스

이 프로젝트는 부트캠프 팀 과제로 제작되었으며, 교육 목적으로만 사용됩니다.

## 참고 자료

- [DART Open API 공식 문서](https://opendart.fss.or.kr/guide/main.do)
- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [MySQL 공식 문서](https://dev.mysql.com/doc/)
