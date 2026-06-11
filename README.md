# AI Smart Classroom System (Flask + MySQL + YOLOv8)

An AI-powered classroom management system that automates attendance tracking and monitors student engagement using computer vision techniques.

## Features

* **Automatic Face Recognition Attendance**

  * Detects and identifies registered students
  * Marks attendance automatically

* **Student Engagement Monitoring**

  * Tracks student behavior during lectures
  * Detects:

    * Face visibility
    * Eye movement
    * Head position
    * Mobile phone usage

* **Real-Time Student Tracking**

  * Monitors multiple students simultaneously
  * Generates engagement scores

* **Web Dashboard**

  * Attendance records
  * Student engagement reports
  * Analytics and summaries

* **Database Integration**

  * Stores attendance records
  * Stores engagement metrics
  * Maintains student information

## Technology Stack

* Python
* Flask
* OpenCV
* YOLOv8 (Ultralytics)
* MySQL
* HTML
* CSS
* JavaScript

## Project Structure

```text
.
├── app.py
├── config.py
├── yolov8n.pt
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
└── README.md
```

## How It Works

### 1) Student Recognition

* Live classroom video is captured through a camera.
* YOLOv8 detects students in the frame.
* Face recognition identifies registered students.
* Attendance is marked automatically.

### 2) Engagement Analysis

The system continuously analyzes student behavior using computer vision techniques:

* Face visibility
* Eye movement
* Head orientation
* Mobile phone usage

Based on these indicators, an engagement score is calculated for each student.

### 3) Attendance Management

* Attendance records are generated automatically.
* Data is stored in the database.
* Historical attendance can be viewed through the dashboard.

### 4) Dashboard & Analytics

The web dashboard provides:

* Attendance summaries
* Student engagement scores
* Analytical reports
* Classroom performance insights

## AI Models

### YOLOv8

The system uses YOLOv8 for real-time object detection and student tracking.

### Face Recognition

Face recognition is used to identify registered students and automate attendance marking.

## Database

The database stores:

* Student information
* Attendance records
* Engagement scores
* System logs

## Setup & Run

### 1) Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 2) Install Dependencies

```bash
pip install -r requirements.txt
```

### 3) Start the Application

```bash
python app.py
```

### 4) Open in Browser

```text
http://127.0.0.1:5000
```

## Screenshots

### Login Page

![Login](screenshots/login.png)

### Dashboard

![Dashboard](screenshots/dashboard.png)

### Attendance Monitoring

![Attendance](screenshots/attendance.png)

### Engagement Analysis

![Engagement](screenshots/engagement.png)

## Future Improvements

* Email notifications
* Mobile application support
* Cloud deployment
* Advanced engagement analytics
* Multi-camera classroom support

## Author

Anuj Srivastava

Aspiring Full-Stack Developer | Python | Flask | Computer Vision | Data Science


