setInterval(() => {
    fetch('/api/active_students')
        .then(response => response.json())
        .then(students => {
            const list = document.getElementById('student-list');
            list.innerHTML = '';

            if (students.length === 0) {
                list.innerHTML = '<div class="student">No recognized active students</div>';
                return;
            }

            students.forEach(student => {
                const div = document.createElement('div');
                div.className = 'student';

                div.innerHTML = `
                    <div class="name">${student.name}</div>
                    <div class="score">${student.score}%</div>
                `;

                list.appendChild(div);
            });
        })
        .catch(() => {
            const list = document.getElementById('student-list');
            list.innerHTML = '<div class="student">Monitor data unavailable</div>';
        });
}, 2000);