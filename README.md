📌 QR-Based Smart Attendance System

📖 Project Overview

This is a QR-based smart attendance system built using Python and Flask.
It allows teachers to generate a QR code for a session, and students can scan it to mark their attendance securely.

The system includes:

- Admin panel for managing students
- Device binding for security
- Email confirmation for attendance proof
- Excel report generation

---

🚀 Features

- 📷 QR Code based attendance
- ⏱️ Time-limited QR (expires automatically)
- 🔐 Device binding (one student = one device)
- 🚫 Duplicate attendance prevention
- 🎓 Branch & Year validation
- 📧 Email confirmation after attendance
- 📊 Excel export of attendance
- 👨‍💻 Admin panel (add/remove students)

---

🧠 Tech Stack

Backend

- Python
- Flask

Database

- PostgreSQL (via psycopg2)

Frontend

- HTML
- CSS (Tailwind CSS)
- JavaScript (Fetch API)

Libraries Used

- qrcode → Generate QR codes
- Pillow → Image processing (required for QR)
- openpyxl → Excel file generation
- smtplib → Sending emails

---

📂 Project Structure

QR-Attendance-System/
│
├── app.py
├── requirements.txt
├── Procfile
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── session.html
│   ├── student.html
│   ├── admin_login.html
│   └── admin_dashboard.html
│
├── static/
│   ├── style.css
│   └── script.js

---

⚙️ Setup Instructions (Step-by-Step)

1️⃣ Clone the repository

git clone https://github.com/imposterji/qr-attendance-system.git
cd qr-attendance-system

---

2️⃣ Create Virtual Environment

python -m venv venv

Activate:

Windows:

venv\Scripts\activate

---

3️⃣ Install Dependencies

pip install -r requirements.txt

---

4️⃣ Setup PostgreSQL Database

1. Open pgAdmin
2. Create a database:

attendance_db

3. Create table:

CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    roll VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    email VARCHAR(100),
    branch VARCHAR(50),
    year VARCHAR(10),
    device TEXT
);

---

5️⃣ Update Database Connection

In "app.py":

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="attendance_db",
        user="postgres",
        password="your_password"
    )

---

6️⃣ Setup Email (IMPORTANT)

1. Enable 2-Step Verification on Gmail
2. Generate App Password
3. Replace in code:

sender_email = "your_email@gmail.com"
app_password = "your_16_digit_password"

---

7️⃣ Run the Project

python app.py

Open browser:

http://localhost:5000

---

📱 How It Works

1. Teacher logs in
2. Starts attendance session
3. QR code is generated
4. Student scans QR
5. Enters roll number
6. System verifies:
   - QR validity
   - Device binding
   - Branch & year
7. Attendance is marked
8. Email confirmation sent

---

🔐 Security Features

- Session-based QR token
- Time-based QR expiry
- Device binding system
- Duplicate entry prevention
- Branch/year validation

---

⚠️ Challenges Faced

- QR reuse problem
- Device duplication issue
- IP/network dependency
- Database integration
- Email authentication setup

---

🚀 Future Enhancements

- Face recognition
- Location-based attendance
- Mobile application
- Cloud deployment
- Analytics dashboard

---

👨‍💻 Author

Developed by: Saniya Sahoo

---

⭐ Notes

This project is built for learning and demonstration purposes, and can be extended into a production-level system with further enhancements.

---
