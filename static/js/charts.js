// Chart.js dashboard charts

function initCharts(dailyData, monthlyData, studentData) {
    // Daily bar
    const dailyCtx = document.getElementById('dailyChart').getContext('2d');
    new Chart(dailyCtx, {
        type: 'bar',
        data: {
            labels: dailyData.map(d => d.date),
            datasets: [{
                label: 'Attendance Count',
                data: dailyData.map(d => d.count),
                backgroundColor: 'rgba(75, 192, 192, 0.6)'
            }]
        },
        options: { scales: { y: { beginAtZero: true } } }
    });
    
    // Monthly line
    const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
    new Chart(monthlyCtx, {
        type: 'line',
        data: {
            labels: monthlyData.map(d => d.month),
            datasets: [{
                label: 'Monthly Attendance',
                data: monthlyData.map(d => d.count),
                borderColor: 'rgba(153, 102, 255, 1)'
            }]
        }
    });
    
    // Student pie
    const studentCtx = document.getElementById('studentChart').getContext('2d');
    new Chart(studentCtx, {
        type: 'doughnut',
        data: {
            labels: studentData.map(s => s.name),
            datasets: [{
                data: studentData.map(s => s.perc),
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            }]
        },
        options: { plugins: { legend: { position: 'right' } } }
    });
}

