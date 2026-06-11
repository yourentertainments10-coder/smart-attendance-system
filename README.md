# AI-Powered Smart Attendance and Engagement Monitoring System

## Overview

Smart Attendance System is an AI-powered classroom management platform that automates attendance tracking and monitors student engagement using computer vision techniques. The system combines face recognition, real-time student tracking, and behavioral analysis to reduce manual effort, improve attendance accuracy, and provide meaningful insights into classroom participation. A web-based dashboard allows administrators and teachers to view attendance records, engagement scores, and analytical reports in an organized manner.

## Features

* Automated Attendance Tracking
* Face Detection and Recognition
* Secure User Authentication
* Student Registration and Management
* Real-Time Attendance Recording
* Attendance Reports and Analytics
* Admin Dashboard
* Database Integration
* Modular Flask Architecture

## Tech Stack

| Technology | Purpose               |
| ---------- | --------------------- |
| Python     | Backend Logic         |
| Flask      | Web Framework         |
| OpenCV     | Computer Vision       |
| YOLOv8     | Object/Face Detection |
| MySQL      | Database Management   |
| HTML       | Frontend Structure    |
| CSS        | Styling               |
| JavaScript | Interactivity         |

## Project Structure

```text
smart-attendance-system/
│
├── database/
├── docs/
├── models/
├── routes/
├── services/
├── static/
├── templates/
├── tests/
├── utils/
│
├── app.py
├── config.py
├── requirements.txt
├── yolov8n.pt
└── README.md
```

## System Workflow

1. Students enter the classroom and are detected through the camera feed.
2. Face recognition identifies registered students and marks attendance automatically.
3. During the lecture, the system continuously tracks students in real time.
4. Computer vision models analyze engagement indicators such as:

   * Face visibility
   * Eye movement
   * Head position
   * Mobile phone usage
5. An engagement score is calculated for each student based on observed behavior.
6. Attendance and engagement data are stored in the database.
7. The web dashboard displays attendance records, engagement statistics, and analytical reports for teachers and administrators.


## Screenshots

### Login Page

![Login Page](screenshots/login.png)

### Dashboard

![Dashboard](screenshots/dashboard.png)

### Attendance Management

![Attendance](screenshots/attendance.png)

### Face Detection

![Detection](screenshots/detection.png)

## Installation

```bash
git clone https://github.com/yourentertainments10-coder/smart-attendance-system.git

cd smart-attendance-system

pip install -r requirements.txt

python app.py
```

## Future Improvements

* Email Notifications
* Attendance Analytics Dashboard
* Cloud Deployment
* Mobile Application Integration
* Multi-Camera Support

## Author

**Anuj Srivastava**

Aspiring Full-Stack Developer | Python | Flask | React | Data Science
