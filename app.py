from multiprocessing.util import info

from flask import Flask, render_template, request, jsonify, session, redirect, send_file
import io
import base64
import time
import uuid
from openpyxl import Workbook
from datetime import datetime
import psycopg2
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "secret123"

# Fake DB
students_present = set()
used_qr_scans = {}
attendance_data = []
serial_no = 1
used_devices = set()

session_data = {
    "session_token": None,
    "subject": "",
    "branch": "",
    "section": ""
}


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="attendance_db",
        user="postgres",
        password="saniya123"
    )

# ------------------------
# ROUTES
# ------------------------


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        tid = request.form.get("teacher_id")
        pwd = request.form.get("password")

        teachers = {
            "T001": {"password": "teacher123", "name": "Dr. Anil Kumar"},
            "T002": {"password": "teacher456", "name": "Prof. Neha Sharma"}
        }

        if tid in teachers and pwd == teachers[tid]["password"]:
            session["teacher_id"] = tid
            session["teacher_name"] = teachers[tid]["name"]
            return redirect("/dashboard")
        else:
            return "Invalid login ❌"

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    global attendance_data, serial_no

    if "teacher_name" not in session:
        return redirect("/login")

    if request.method == "POST":

        # RESET everything for new session
        used_devices.clear()
        used_qr_scans.clear()

        session_data["subject"] = request.form["subject"]
        session_data["branch"] = request.form["branch"]
        session_data["section"] = request.form["section"]
        session_data["year"] = request.form["year"]
        session_data["session_token"] = str(uuid.uuid4())
        session_data["start_time"] = time.time()
        session_data["start_time_str"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")

        attendance_data.clear()
        serial_no = 1
        students_present.clear()

        return redirect("/session")

    return render_template("dashboard.html")


@app.route("/session")
def session_page():
    if "teacher_name" not in session:
        return redirect("/login")

    return render_template("session.html", teacher=session["teacher_name"])


@app.route("/get_qr")
def get_qr():
    try:
        import qrcode

        token = session_data.get("session_token")

        if not token:
            return jsonify({"qr": "", "count": 0})

        timestamp = int(time.time())
        url = f"url = f"/student?token={token}&t={timestamp}""

        qr = qrcode.make(url)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")

        img_str = base64.b64encode(buffer.getvalue()).decode()

        remaining = 600 - \
            int(time.time() - session_data.get("start_time", time.time()))

        if remaining <= 0:
            session_data["session_token"] = None
            return jsonify({"expired": True})

        return jsonify({
            "qr": img_str,
            "count": len(attendance_data),
            "time_left": remaining
        })

    except Exception as e:
        print("QR ERROR:", e)
        return jsonify({"qr": "", "count": 0})


@app.route("/s")
def short_student():
    token = request.args.get("token")
    t = request.args.get("t")
    return redirect(f"/student?token={token}&t={t}")


@app.route("/student")
def student_page():
    return render_template("student.html")


@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    global serial_no

    token = request.json.get("token")
    student_id = request.json.get("student_id")
    qr_time = request.json.get("time")

    user_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    device_key = user_ip + user_agent

    # ❌ invalid session
    if token != session_data["session_token"]:
        return jsonify({"status": "invalid"})

    # ❌ expired QR
    current_time = int(time.time())
    if current_time - int(qr_time) > 300:
        return jsonify({"status": "expired"})

    # ❌ QR reuse
    qr_key = f"{token}_{qr_time}"
    if qr_key in used_qr_scans:
        prev = used_qr_scans[qr_key]

        if prev["device"] != user_agent:
            return jsonify({"status": "QR already used ❌"})

    # ❌ duplicate student
    for row in attendance_data:
        if row["roll"] == student_id:
            return jsonify({"status": "already marked"})

    # ❌ same device reuse (same session)
    if device_key in used_devices:
        return jsonify({"status": "Device already used ❌"})

    # ✅ DB CHECK
    conn = get_db_connection()
    cur = conn.cursor()

    # 🔍 get branch + year
    cur.execute("SELECT branch, year FROM students WHERE roll = %s", (student_id,))
    info = cur.fetchone()

    # ❌ student not found
    if not info:
        conn.close()
        return jsonify({"status": "Invalid student ❌"})

    student_branch = info[0]
    student_year = info[1]

    # ❌ mismatch block

    if str(student_branch).lower() != str(session_data.get("branch")).lower() \
    or str(student_year) != str(session_data.get("year")):
   
     conn.close()
     return jsonify({"status": "Wrong class ❌"})

    # get student name + email
    cur.execute("SELECT name, email FROM students WHERE roll = %s", (student_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({"status": "Invalid student ❌"})

    student_name = row[0]
    student_email = row[1]

    # 🔍 get saved device
    cur.execute("SELECT device FROM students WHERE roll = %s", (student_id,))
    row_device = cur.fetchone()

    saved_device = row_device[0] if row_device else None

    # 🟢 FIRST TIME → register device
    if saved_device is None:
        cur.execute(
            "UPDATE students SET device = %s WHERE roll = %s",
            (device_key, student_id)
        )
        conn.commit()

    # 🔴 DIFFERENT DEVICE → BLOCK
    elif saved_device != device_key:
        conn.close()
        return jsonify({"status": "Unauthorized device ❌"})

    conn.close()

    # ✅ SAVE ATTENDANCE
    attendance_data.append({
        "serial": serial_no,
        "roll": student_id,
        "name": student_name,
        "time": datetime.now().strftime("%H:%M:%S"),
        "token": token,
        "qr_time": qr_time,
        "ip": user_ip,
        "device": user_agent
    })

    # mark QR used
    used_qr_scans[qr_key] = {
        "ip": user_ip,
        "device": user_agent
    }

    # mark device used
    used_devices.add(device_key)

    serial_no += 1

    # 📧 send mail
    send_mail(student_email, student_name, session_data["subject"])

    return jsonify({"status": "marked"})


@app.route("/download_excel")
def download_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"

    # 🔥 TOP HEADING BLOCK
    ws.append(["ATTENDANCE REPORT"])
    ws.append([])

    ws.append(["Teacher:", session.get("teacher_name")])
    ws.append(["Subject:", session_data.get("subject")])
    ws.append(["Branch:", session_data.get("branch")])
    ws.append(["Section:", session_data.get("section")])
    ws.append(["Session Start:", session_data.get("start_time_str")])

    ws.append([])  # space

    # 🔽 TABLE HEADER
    ws.append([
        "S.No", "Roll No", "Name", "Student Time",
        "QR Token", "IP Address", "Device"
    ])

    # 🔽 DATA
    for row in attendance_data:
        ws.append([
            row["serial"],
            row["roll"],
            row["name"],
            row["time"],
            row["token"],
            row.get("ip", ""),
            row.get("device", "")
        ])

    filename = f"attendance_{datetime.now().strftime('%H%M%S')}.xlsx"
    wb.save(filename)

    return send_file(filename, as_attachment=True)

@app.route("/end_session")
def end_session():
    session.clear()   # 🔥 logout
    session_data["session_token"] = None
    return redirect("/login")


@app.route("/get_attendance")
def get_attendance():
    return jsonify({
        "students": attendance_data
    })


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/admin/dashboard")
        else:
            return "Invalid admin login ❌"

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT roll, name, email FROM students")
    students = cur.fetchall()

    conn.close()

    return render_template("admin_dashboard.html", students=students)


@app.route("/admin/add_student", methods=["POST"])
def add_student():
    if "admin" not in session:
        return redirect("/admin")

    roll = request.form.get("roll")
    name = request.form.get("name")
    email = request.form.get("email")
    branch = request.form.get("branch")
    year = request.form.get("year")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
        "INSERT INTO students (roll, name, email, branch, year) VALUES (%s, %s, %s, %s, %s)",
         (roll, name, email, branch, year)
    )
        conn.commit()

    except Exception as e:
        conn.rollback()
        return "Roll number already exists ❌"

    finally:
        conn.close()

    return redirect("/admin/dashboard")


@app.route("/admin/delete/<roll>")
def delete_student(roll):
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM students WHERE roll=%s", (roll,))
    conn.commit()
    conn.close()

    return redirect("/admin/dashboard")


def send_mail(to_email, student_name, subject):
    sender_email = "hunextra2@gmail.com"
    app_password = "nvihvwmtstrvlcwz"

    try:
        msg = MIMEText(f"""
    Hello {student_name},

    Your attendance has been successfully marked.

    Subject: {subject}
    Time: {datetime.now().strftime("%H:%M:%S")}

    Thank you
    """)

        msg["Subject"] = "Attendance Confirmation"
        msg["From"] = sender_email
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print("✅ MAIL SENT")

    except Exception as e:
        print("❌ MAIL ERROR:", e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
