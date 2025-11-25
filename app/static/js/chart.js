// Chart.js를 사용한 차트 생성 함수들

function initChart1(corpName) {
    if (!corpName) return;
    
    fetch(`/chart1_data/${corpName}`)
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById('chart1');
            if (!ctx) return;
            
            new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.years,
                    datasets: [{
                        label: '자산총계',
                        data: data.amounts,
                        borderColor: 'blue',
                        fill: false,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true
                }
            });
        })
        .catch(error => {
            console.error('Chart1 데이터 로드 실패:', error);
        });
}

function initChart2(corpName, year) {
    if (!corpName || !year) return;
    
    fetch(`/chart2_data/${corpName}/${year}`)
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById('chart2');
            if (!ctx) return;
            
            new Chart(ctx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.accounts,
                    datasets: [{
                        label: `${year}년 금액`,
                        data: data.amounts,
                        backgroundColor: 'orange'
                    }]
                },
                options: {
                    responsive: true
                }
            });
        })
        .catch(error => {
            console.error('Chart2 데이터 로드 실패:', error);
        });
}

// 페이지 로드 시 차트 초기화
document.addEventListener('DOMContentLoaded', function() {
    const chartContainer = document.querySelector('[data-chart-container]');
    if (!chartContainer) return;
    
    const corpName = chartContainer.dataset.corpName || null;
    const year = chartContainer.dataset.year || null;
    
    if (corpName) {
        initChart1(corpName);
    }
    
    if (corpName && year) {
        initChart2(corpName, year);
    }
});

