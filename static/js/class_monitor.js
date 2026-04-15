setInterval(() => {
fetch('/api/active_students')
        .then(response => response.json())
        .then(students => {
            const list = document.getElementById('student-list');
            list.innerHTML = '';

            if (!students.length) {
                list.innerHTML = '<div class="student">No recognized active students</div>';
                return;
            }

            students.forEach(student => {
                const div = document.createElement('div');
                div.className = 'student';
                if (student.status === 'debug') {
                    div.style.background = '#555';
                }
                div.innerHTML = `
                    <div class="name">${student.name}</div>
                    <div class="score">${student.engagement ? (student.engagement * 100).toFixed(1) + '%' : '0%'}</div>
                    ${student.phone ? '<span class="phone">??</span>' : ''}
                `;
                list.appendChild(div);
            });
        })
        .catch(() => {
            const list = document.getElementById('student-list');
            list.innerHTML = '<div class="student">Monitor data unavailable</div>';
        });
}, 2000);
