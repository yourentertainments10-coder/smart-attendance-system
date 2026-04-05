-- Seed sample students
INSERT OR IGNORE INTO students (student_id, name, folder_name) VALUES 
('101', 'John Doe', '101_John_Doe'),
('102', 'Jane Smith', '102_Jane_Smith'),
('103', 'Bob Johnson', '103_Bob_Johnson');

-- Sample attendance
INSERT OR IGNORE INTO attendance (student_id, date, recognized_name) VALUES 
('101', date('now'), '101_John_Doe'),
('102', date('now'), '102_Jane_Smith');