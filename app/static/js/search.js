document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const corpList = document.getElementById('corpList');
    const corpListContent = document.getElementById('corpListContent');
    const loading = document.getElementById('loading');
    
    // 검색 URL 가져오기 (전역 변수에서 또는 기본값 사용)
    const searchActionUrl = window.SEARCH_URL || '/search';
    
    // 검색 버튼 클릭
    searchBtn.addEventListener('click', function() {
        performSearch();
    });
    
    // Enter 키 입력
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch();
        }
    });
    
    function performSearch() {
        const searchTerm = searchInput.value.trim();
        
        if (searchTerm.length < 1) {
            corpList.style.display = 'none';
            return;
        }
        
        // 기업 목록 검색
        fetch(`/api/search_corps?q=${encodeURIComponent(searchTerm)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    corpListContent.innerHTML = '<p style="padding: 10px; color: red;">오류: ' + data.error + '</p>';
                    corpList.style.display = 'block';
                    return;
                }
                
                if (data.corps && data.corps.length > 0) {
                    let html = '<div style="padding: 10px;">';
                    data.corps.forEach(function(corp) {
                        html += '<div class="corp-item" style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; transition: background-color 0.2s;" ';
                        html += 'onmouseover="this.style.backgroundColor=\'#f5f5f5\'" ';
                        html += 'onmouseout="this.style.backgroundColor=\'white\'" ';
                        html += `onclick="selectCorp('${corp.corp_name.replace(/'/g, "\\'")}')">`;
                        html += '<strong>' + corp.corp_name + '</strong>';
                        html += '<span style="color: #666; margin-left: 10px;">(' + corp.corp_code + ')</span>';
                        html += '</div>';
                    });
                    html += '</div>';
                    corpListContent.innerHTML = html;
                    corpList.style.display = 'block';
                } else {
                    corpListContent.innerHTML = '<p style="padding: 10px;">검색 결과가 없습니다.</p>';
                    corpList.style.display = 'block';
                }
            })
            .catch(error => {
                corpListContent.innerHTML = '<p style="padding: 10px; color: red;">검색 중 오류가 발생했습니다: ' + error + '</p>';
                corpList.style.display = 'block';
            });
    }
    
    // 기업 선택 시 재무제표 조회
    window.selectCorp = function(corpName) {
        loading.style.display = 'block';
        corpList.style.display = 'none';
        
        // 폼 생성하여 POST 요청
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = searchActionUrl;
        
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'corp_name';
        input.value = corpName;
        
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    };
});

