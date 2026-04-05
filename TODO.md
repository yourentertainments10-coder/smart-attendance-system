# Smart Attendance System - Development TODO

## Completed Steps
- [x] Step 5: Face Recognition (MSE matching)


## Step 6 - Database Setup ✓
- [x] config.py DATABASE path
- [x] db_connection.py Flask SQLite get_db
- [x] schema.sql students + attendance tables (refined schema)
- [x] seed_data.sql samples
- [x] app.py /init_db exec schema + seed
- [x] Test insert/fetch (run /init_db to create smart_attendance.db)


## Notes
- students: id, student_id TEXT UNIQUE, name TEXT, folder_name TEXT
- attendance: id, student_id TEXT, date TEXT, time TEXT, UNIQUE(student_id, date)
