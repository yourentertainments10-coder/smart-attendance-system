// Chart.js dashboard charts - Enhanced with engagement
window.dailyChart = null;
window.monthlyChart = null;
window.studentChart = null;
window.engagementChart = null;
function initCharts(dailyData, monthlyData, studentData, engagementData = []) {
  // Destroy existing charts if exist to avoid duplicates
if (window.dailyChart && typeof window.dailyChart.destroy === "function") {
  window.dailyChart.destroy();
}
if (window.monthlyChart && typeof window.monthlyChart.destroy === "function") {
  window.monthlyChart.destroy();
}
if (window.studentChart && typeof window.studentChart.destroy === "function") {
  window.studentChart.destroy();
}
if (window.engagementChart && typeof window.engagementChart.destroy === "function") {
  window.engagementChart.destroy();
}

  // Daily bar
  const dailyCtx = document.getElementById('dailyChart').getContext('2d');
  window.dailyChart = new Chart(dailyCtx, {
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
  window.monthlyChart = new Chart(monthlyCtx, {
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
  
  // Student attendance doughnut
  const studentCtx = document.getElementById('studentChart').getContext('2d');
  window.studentChart = new Chart(studentCtx, {
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

  // Engagement bar chart (green/high, red/low)
  const engagementCtx = document.getElementById('engagementChart')?.getContext('2d');
  if (engagementCtx && engagementData.length > 0) {
    window.engagementChart = new Chart(engagementCtx, {
      type: 'bar',
      data: {
        labels: engagementData.map(e => e.id),
        datasets: [{
          label: 'Avg Engagement %',
          data: engagementData.map(e => e.avg || 0),
          backgroundColor: engagementData.map(e => (e.avg || 0) > 70 ? 'rgba(75, 192, 75, 0.8)' : 'rgba(255, 99, 132, 0.6)')
        }]
      },
      options: { 
        scales: { y: { beginAtZero: true, max: 100 } },
        plugins: { legend: { display: false } }
      }
    });
  }
}
