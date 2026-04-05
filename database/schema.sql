-- Students table
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    folder_name TEXT NOT NULL,
    created DATE DEFAULT (date('now'))
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    recognized_name TEXT,
    FOREIGN KEY (student_id) REFERENCES students (student_id),
    UNIQUE(student_id, date)
);

-- Engagement table
CREATE TABLE IF NOT EXISTS engagement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date TEXT NOT NULL,
    avg_engagement REAL,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);


CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
