from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, smtplib, ssl, secrets, string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------------------
# Hardcoded Admin
# ---------------------------
ADMIN_USER = {"username": "admin", "password": "password123"}

# ---------------------------
# Database Setup
# ---------------------------
def init_db():
    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS Lecturers (
            Lecturer_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            First_Name TEXT NOT NULL,
            Last_Name TEXT NOT NULL,
            Email TEXT NOT NULL UNIQUE,
            Phone_Number TEXT,
            Department TEXT,
            Username TEXT UNIQUE,
            Password TEXT,
            Date_Created TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS Modules (
        Module_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Module_Code TEXT NOT NULL UNIQUE,
        Module_Name TEXT NOT NULL,
        Description TEXT,
        Credits INTEGER,
        Semester TEXT,
        Department TEXT,
        Lecturer_ID INTEGER,
        Number_of_Classes INTEGER,
        Date_Created TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (Lecturer_ID) REFERENCES Lecturers(Lecturer_ID)
    )
""")
    
    # Students table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Students (
            Student_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            First_Name TEXT NOT NULL,
            Last_Name TEXT NOT NULL,
            Student_Number TEXT NOT NULL UNIQUE,
            Email TEXT NOT NULL UNIQUE,
            Password TEXT NOT NULL,
            Date_Created TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Junction table for many-to-many: Students <-> Modules
    c.execute("""
        CREATE TABLE IF NOT EXISTS StudentModules (
            Student_ID INTEGER,
            Module_ID INTEGER,
            FOREIGN KEY (Student_ID) REFERENCES Students(Student_ID),
            FOREIGN KEY (Module_ID) REFERENCES Modules(Module_ID),
            PRIMARY KEY (Student_ID, Module_ID)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------------------
# Email Config (Gmail)
# ---------------------------
SENDER_EMAIL = "mpilozikhali72@gmail.com"      # 👈 replace with your Gmail
SENDER_PASSWORD = "etvn fogt ndvv lcse"     # 👈 replace with your Gmail app password

def send_login_email(receiver_email, username, password):
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your Face Logged Account Details"
        message["From"] = SENDER_EMAIL
        message["To"] = receiver_email

        text = f"""
        Hello,

        Your lecturer account has been created.

        Username: {username}
        Password: {password}

        Please log in and change your password after first login.

        Regards,
        Face Logged Admin
        """
        message.attach(MIMEText(text, "plain"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())

        print("✅ Email sent to:", receiver_email)

    except Exception as e:
        print("❌ Email sending failed:", e)

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    if request.args.get("loaded") == "true":
        return render_template("index.html")  # Main homepage
    return render_template("loader.html")     # Loader page


# ---------- Login (Admin + Lecturers) ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Admin login
        if username == ADMIN_USER["username"] and password == ADMIN_USER["password"]:
            session["role"] = "admin"
            session["logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        # Lecturer login
        conn = sqlite3.connect("face_logged.db")
        c = conn.cursor()
        c.execute("SELECT * FROM Lecturers WHERE Username = ? AND Password = ?", (username, password))
        lecturer = c.fetchone()
        conn.close()

        if lecturer:
            session["role"] = "lecturer"
            session["logged_in"] = True
            session["lecturer_id"] = lecturer[0]  # store Lecturer_ID
            return redirect(url_for("lecturer_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# ---------- Admin Dashboard ----------
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

# ---------- Lecturer Dashboard ----------
@app.route("/lecturer-dashboard")
def lecturer_dashboard():
    if not session.get("logged_in") or session.get("role") != "lecturer":
        return redirect(url_for("login"))

    lecturer_id = session.get("lecturer_id")
    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("SELECT * FROM Lecturers WHERE Lecturer_ID = ?", (lecturer_id,))
    lecturer = c.fetchone()
    conn.close()

    return render_template("lecturer_dashboard.html", lecturer=lecturer)

# ---------- View All Lecturers (Admin Only) ----------
@app.route("/lecturers")
def lecturers():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("SELECT * FROM Lecturers")
    lecturers_list = c.fetchall()
    conn.close()
    return render_template("lecturers.html", lecturers=lecturers_list)

# ---------- Add Lecturer (Admin Only) ----------
@app.route("/add-lecturer", methods=["GET", "POST"])
def add_lecturer():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        department = request.form.get("department")
        username = request.form.get("username")

        # Generate random password
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(10))

        # Save to DB
        conn = sqlite3.connect("face_logged.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO Lecturers (First_Name, Last_Name, Email, Phone_Number, Department, Username, Password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, department, username, password))
        conn.commit()
        conn.close()

        # Send credentials via email
        send_login_email(email, username, password)

        return redirect(url_for("lecturers"))

    return render_template("add_lecturer.html")

# ---------- Delete Lecturer (Admin Only) ----------
@app.route("/delete-lecturer/<int:lecturer_id>", methods=["POST"])
def delete_lecturer(lecturer_id):
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("DELETE FROM Lecturers WHERE Lecturer_ID = ?", (lecturer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("lecturers"))

@app.route("/add-module", methods=["GET", "POST"])
def add_module():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("SELECT * FROM Lecturers")
    lecturers = c.fetchall()
    conn.close()

    if request.method == "POST":
        module_code = request.form.get("module_code")
        module_name = request.form.get("module_name")
        description = request.form.get("description")
        credits = request.form.get("credits")
        semester = request.form.get("semester")
        department = request.form.get("department")
        lecturer_id = request.form.get("lecturer_id")
        number_of_classes = request.form.get("number_of_classes")

        conn = sqlite3.connect("face_logged.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO Modules
            (Module_Code, Module_Name, Description, Credits, Semester, Department, Lecturer_ID, Number_of_Classes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (module_code, module_name, description, credits, semester, department, lecturer_id, number_of_classes))
        conn.commit()
        conn.close()

        return redirect(url_for("modules"))  # create a page to list all modules

    return render_template("add_module.html", lecturers=lecturers)
# ---------- View All Modules (Admin Only) ----------
@app.route("/modules")
def modules():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("""
        SELECT m.Module_ID, m.Module_Code, m.Module_Name, m.Description, m.Credits,
               m.Semester, m.Department, l.First_Name, l.Last_Name, m.Number_of_Classes
        FROM Modules m
        LEFT JOIN Lecturers l ON m.Lecturer_ID = l.Lecturer_ID
    """)
    modules_list = c.fetchall()
    conn.close()
    return render_template("modules.html", modules=modules_list)
@app.route("/students")
def students():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("SELECT * FROM Students")
    students_list = c.fetchall()
    conn.close()

    return render_template("students.html", students=students_list, get_modules_for_student=get_modules_for_student)

@app.route("/add-student", methods=["GET", "POST"])
def add_student():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login"))

    # get all modules for multi-select dropdown
    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("SELECT Module_ID, Module_Name FROM Modules")
    modules = c.fetchall()
    conn.close()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        student_number = request.form.get("student_number")
        email = request.form.get("email")
        password = request.form.get("password")  # created by admin
        selected_modules = request.form.getlist("modules")  # list of module_ids

        conn = sqlite3.connect("face_logged.db")
        c = conn.cursor()

        # Check for duplicates
        c.execute("SELECT * FROM Students WHERE Email = ? OR Student_Number = ?", (email, student_number))
        existing = c.fetchone()

        if existing:
            conn.close()
            flash("⚠️ A student with this email or student number already exists!", "danger")
            return redirect(url_for("add_student"))

        # Insert student
        c.execute("""
            INSERT INTO Students (First_Name, Last_Name, Student_Number, Email, Password)
            VALUES (?, ?, ?, ?, ?)
        """, (first_name, last_name, student_number, email, password))
        student_id = c.lastrowid

        # Assign modules
        for module_id in selected_modules:
            c.execute("""
                INSERT INTO StudentModules (Student_ID, Module_ID)
                VALUES (?, ?)
            """, (student_id, module_id))

        conn.commit()
        conn.close()

        # send email
        try:
            send_login_email(email, student_number, password)
            flash("✅ Student added successfully and login details sent via email!", "success")
        except Exception as e:
            flash(f"⚠️ Student added, but email could not be sent. Error: {str(e)}", "warning")

        return redirect(url_for("students"))

    return render_template("add_student.html", modules=modules)

def get_modules_for_student(student_id):
    conn = sqlite3.connect("face_logged.db")
    c = conn.cursor()
    c.execute("""
        SELECT m.Module_ID, m.Module_Code, m.Module_Name
        FROM StudentModules sm
        JOIN Modules m ON sm.Module_ID = m.Module_ID
        WHERE sm.Student_ID = ?
    """, (student_id,))
    modules = c.fetchall()
    conn.close()
    return modules



# ---------- Logout ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)









