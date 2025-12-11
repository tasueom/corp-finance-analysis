// ------------------------------
// 연도 목록 불러오기
// ------------------------------
function loadYears(selectElem) {
    const corp = selectElem.value;

    // 현재 행(.compare-row)을 기준으로 year select 찾기
    const row = selectElem.closest(".compare-row");
    const yearBox = row.querySelector('select[name="year"]');

    if (!corp) {
        yearBox.innerHTML = "";
        return;
    }

    fetch(`/api/get_years?corp=${corp}`)
        .then(res => res.json())
        .then(data => {
            yearBox.innerHTML = "";

            data.years.forEach(year => {
                yearBox.innerHTML += `<option value="${year}">${year}</option>`;
            });
        });
}



// ------------------------------
// 비교 행 추가 버튼 기능
// ------------------------------
document.addEventListener("DOMContentLoaded", function () {

    const addBtn = document.getElementById("add-btn");
    const compareBox = document.getElementById("compare-box");

    addBtn.addEventListener("click", function () {

        // 새로운 비교 행 HTML
        const newRow = document.createElement("div");
        newRow.classList.add("compare-row", "row-box");
        newRow.innerHTML = `
            <div>
                <label>기업 선택</label>
                <select name="corp_name" onchange="loadYears(this)">
                    <option value="">기업 선택</option>
                    ${getCorpOptions()}
                </select>
            </div>

            <div>
                <label>연도 선택</label>
                <select name="year"></select>
            </div>
        `;

        compareBox.appendChild(newRow);
    });
});



// ------------------------------
// 기업 선택 옵션 HTML 생성
// ------------------------------
function getCorpOptions() {
    // HTML 템플릿 내부에서 corp_list 를 JS로 넘기기 위해 템플릿에서 embed 필요
    // compare.html 상단에서 다음 코드 추가해야 함:
    // <script>const corpList = {{ corp_list | tojson }};</script>

    let html = "";

    corpList.forEach(corp => {
        html += `<option value="${corp[0]}">${corp[0]}</option>`;
    });

    return html;
}
