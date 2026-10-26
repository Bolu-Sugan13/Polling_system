from flask import Flask, render_template, request, redirect, session
import sqlite3
app = Flask(__name__)
app.secret_key = "cr_election_secret_key"
DATABASE = "poll.db"
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def create_database():
    conn = get_db()
    cursor = conn.cursor()
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)
    # Candidates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            slogan TEXT NOT NULL,
            votes INTEGER DEFAULT 0
        )
    """)
    # Admin table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # Poll table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS poll (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'closed'
        )
    """)
    # Create default admin
    cursor.execute("SELECT * FROM admin")
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO admin (username, password)
            VALUES (?, ?)
        """, ("admin", "admin123"))
    # Create poll
    cursor.execute("SELECT * FROM poll")
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO poll (id, title, status)
            VALUES (1, ?, ?)
        """, ("CR Election 2026", "closed"))
    # Create sample candidates
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]
    if count == 0:
        candidates = [
            ("Arun", "MCA", "Leadership • Unity • Voice"),
            ("Priya", "MCA", "Together We Grow"),
            ("Rahul", "MCA", "Your Voice, Your CR")
        ]
        cursor.executemany("""
            INSERT INTO candidates
            (name, department, slogan)
            VALUES (?, ?, ?)
        """, candidates)
    conn.commit()
    conn.close()
@app.route("/")
def home():
    conn = get_db()
    poll = conn.execute(
        "SELECT * FROM poll WHERE id = 1"
    ).fetchone()
    candidates = conn.execute(
        "SELECT * FROM candidates ORDER BY votes DESC"
    ).fetchall()
    conn.close()
    return render_template(
        "index.html",
        poll=poll,
        candidates=candidates
    )
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        name = request.form["name"]
        roll_no = request.form["roll_no"]
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO students
                (name, roll_no, email, password)
                VALUES (?, ?, ?, ?)
            """, (name, roll_no, email, password))
            conn.commit()
            message = "Registration successful! Please login."
        except sqlite3.IntegrityError:
            message = "Roll number already registered."
        conn.close()
    return render_template(
        "register.html",
        message=message
    )
@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    message = ""
    if request.method == "POST":
        roll_no = request.form["roll_no"]
        password = request.form["password"]
        conn = get_db()
        student = conn.execute("""
            SELECT * FROM students
            WHERE roll_no = ? AND password = ?
        """, (roll_no, password)).fetchone()
        conn.close()
        if student:
            session["student_id"] = student["id"]
            session["student_name"] = student["name"]
            return redirect("/vote")
        else:
            message = "Invalid roll number or password."
    return render_template(
        "student_login.html",
        message=message
    )
@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "student_id" not in session:
        return redirect("/student_login")
    conn = get_db()
    poll = conn.execute(
        "SELECT * FROM poll WHERE id = 1"
    ).fetchone()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (session["student_id"],)
    ).fetchone()
    candidates = conn.execute(
        "SELECT * FROM candidates"
    ).fetchall()
    if request.method == "POST":
        if poll["status"] != "open":
            conn.close()
            return render_template(
                "vote.html",
                poll=poll,
                candidates=candidates,
                message="Polling is currently closed."
            )
        if student["has_voted"] == 1:
            conn.close()
            return render_template(
                "vote.html",
                poll=poll,
                candidates=candidates,
                message="You have already voted."
            )
        candidate_id = request.form["candidate"]
        conn.execute("""
            UPDATE candidates
            SET votes = votes + 1
            WHERE id = ?
        """, (candidate_id,))
        conn.execute("""
            UPDATE students
            SET has_voted = 1
            WHERE id = ?
        """, (session["student_id"],))
        conn.commit()
        conn.close()
        return render_template(
            "vote.html",
            poll=poll,
            candidates=candidates,
            message="Your vote has been successfully recorded!"
        )
    conn.close()
    return render_template(
        "vote.html",
        poll=poll,
        candidates=candidates,
        message=""
    )
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    message = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        admin = conn.execute("""
            SELECT * FROM admin
            WHERE username = ? AND password = ?
        """, (username, password)).fetchone()
        conn.close()
        if admin:
            session["admin"] = username
            return redirect("/admin")
        else:
            message = "Invalid admin username or password."
    return render_template(
        "admin_login.html",
        message=message
    )
@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/admin_login")
    conn = get_db()
    poll = conn.execute(
        "SELECT * FROM poll WHERE id = 1"
    ).fetchone()
    candidates = conn.execute(
        "SELECT * FROM candidates ORDER BY votes DESC"
    ).fetchall()
    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()
    conn.close()
    return render_template(
        "admin_dashboard.html",
        poll=poll,
        candidates=candidates,
        students=students
    )
@app.route("/start_poll")
def start_poll():
    if "admin" not in session:
        return redirect("/admin_login")
    conn = get_db()
    conn.execute("""
        UPDATE poll
        SET status = 'open'
        WHERE id = 1
    """)
    conn.commit()
    conn.close()
    return redirect("/admin")
@app.route("/close_poll")
def close_poll():
    if "admin" not in session:
        return redirect("/admin_login")
    conn = get_db()
    conn.execute("""
        UPDATE poll
        SET status = 'closed'
        WHERE id = 1
    """)
    conn.commit()
    conn.close()
    return redirect("/admin")
@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    if "admin" not in session:
        return redirect("/admin_login")
    name = request.form["name"]
    department = request.form["department"]
    slogan = request.form["slogan"]
    conn = get_db()
    conn.execute("""
        INSERT INTO candidates
        (name, department, slogan)
        VALUES (?, ?, ?)
    """, (name, department, slogan))
    conn.commit()
    conn.close()
    return redirect("/admin")
@app.route("/delete_candidate/<int:id>")
def delete_candidate(id):
    if "admin" not in session:
        return redirect("/admin_login")
    conn = get_db()
    conn.execute(
        "DELETE FROM candidates WHERE id = ?",
        (id,)
    )
    conn.commit()
    conn.close()
    return redirect("/admin")
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
if __name__ == "__main__":
    create_database()
    app.run(debug=True)
