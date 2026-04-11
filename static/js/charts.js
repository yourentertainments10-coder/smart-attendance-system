window.dailyChart = null;
window.monthlyChart = null;
window.studentChart = null;
window.engagementChart = null;

function initCharts(dailyData, monthlyData, studentData, engagementData = []) {

  // Destroy old charts
  if (window.dailyChart?.destroy) window.dailyChart.destroy();
  if (window.monthlyChart?.destroy) window.monthlyChart.destroy();
  if (window.studentChart?.destroy) window.studentChart.destroy();
  if (window.engagementChart?.destroy) window.engagementChart.destroy();

  // ✅ Daily Chart
  const dailyEl = document.getElementById('dailyChart');
  if (dailyEl) {
    window.dailyChart = new Chart(dailyEl.getContext('2d'), {
      type: 'bar',
      data: {
        labels: dailyData.map(d => d.date),
        datasets: [{
          label: 'Attendance Count',
          data: dailyData.map(d => d.count),
          backgroundColor: 'rgba(75,192,192,0.6)'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  // ✅ Monthly Chart
  const monthlyEl = document.getElementById('monthlyChart');
  if (monthlyEl) {
    window.monthlyChart = new Chart(monthlyEl.getContext('2d'), {
      type: 'line',
      data: {
        labels: monthlyData.map(d => d.month),
        datasets: [{
          label: 'Monthly Attendance',
          data: monthlyData.map(d => d.count),
          borderColor: 'purple'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // ✅ Student Chart
  const studentEl = document.getElementById('studentChart');
  if (studentEl) {
    window.studentChart = new Chart(studentEl.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: studentData.map(s => s.name),
        datasets: [{
          data: studentData.map(s => s.perc),
          backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right' } }
      }
    });
  }

  // ✅ Engagement Chart
  const engEl = document.getElementById('engagementChart');
  if (engEl && engagementData.length > 0) {
    window.engagementChart = new Chart(engEl.getContext('2d'), {
      type: 'bar',
      data: {
        labels: engagementData.map(e => e.id),
        datasets: [{
          label: 'Engagement %',
          data: engagementData.map(e => e.avg || 0),
          backgroundColor: engagementData.map(e =>
            (e.avg || 0) > 70 ? 'green' : 'red'
          )
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, max: 100 } }
      }
    });
  }
}