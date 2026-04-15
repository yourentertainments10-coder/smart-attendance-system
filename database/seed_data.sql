
-- Seed admin user (scrypt hash for 'admin123')
INSERT OR IGNORE INTO users (username, password_hash) VALUES 
('admin', 'scrypt:32768:8:1$8eGGpuslJaGdLy6b$75fb00328670b5e33d682581db341767e1e9e1310735cc99ccc4c531027fac4a0b82dad5b81e90339b0c2a29152ff0838bb080552aa879248502db96ecf82567');
