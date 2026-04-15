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
    timestamp TEXT,
    avg_engagement REAL,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
);

CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_engagement_student_date ON engagement(student_id, date);
CREATE INDEX IF NOT EXISTS idx_engagement_timestamp ON engagement(timestamp);

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
