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

function initPieChart(corpName, year) {
    if (!corpName || !year) return;
    
    fetch(`/pie_data/${corpName}/${year}`)
        .then(res => res.json())
        .then(data => {
            if (Object.keys(data).length === 0) {
                console.warn('파이 차트 데이터가 없습니다.');
                return;
            }
            
            const ctx = document.getElementById('pieChart');
            if (!ctx) return;
            
            // 자본총계를 먼저, 부채총계를 나중에 오도록 정렬
            const sortedLabels = [];
            const sortedValues = [];
            
            if (data['자본총계'] !== undefined) {
                sortedLabels.push('자본총계');
                sortedValues.push(data['자본총계']);
            }
            if (data['부채총계'] !== undefined) {
                sortedLabels.push('부채총계');
                sortedValues.push(data['부채총계']);
            }
            
            new Chart(ctx.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: sortedLabels,
                    datasets: [{
                        data: sortedValues,
                        backgroundColor: ['#36A2EB', '#FF6384']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.label || '';
                                    let value = context.parsed || 0;
                                    return label + ': ' + value.toLocaleString('ko-KR') + '원';
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('파이 차트 데이터 로드 실패:', error);
        });
}

// 비교 차트 렌더링 함수
let compareChartInstance = null;

function renderCompareChart(data){
    const ctx = document.getElementById('comparisonChart');
    if (!ctx) return;
    
    const chartCtx = ctx.getContext('2d');

    const datasets = Object.keys(data)
        .filter(k => k !== "accounts")
        .map((key, i) => ({
            label: key,
            data: data[key],
            backgroundColor: `hsl(${i * 60 % 360}, 70%, 50%)`
        }));

    if(compareChartInstance) compareChartInstance.destroy(); // 이전 차트 제거

    compareChartInstance = new Chart(chartCtx, {
        type: 'bar',
        data: {
            labels: data.accounts,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                title: { display: true, text: '기업별 계정 비교' }
            }
        }
    });
}

// 페이지 로드 시 차트 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 비교 차트 초기화 (compare.html용)
    if (window.chartData && window.chartData.accounts) {
        renderCompareChart(window.chartData);
    }
    
    // 기존 차트 초기화 (chart.html용)
    const chartContainer = document.querySelector('[data-chart-container]');
    if (!chartContainer) return;
    
    const corpName = chartContainer.dataset.corpName || null;
    const year = chartContainer.dataset.year || null;
    
    if (corpName) {
        initChart1(corpName);
    }
    
    if (corpName && year) {
        initChart2(corpName, year);
        initPieChart(corpName, year);
    }
});

