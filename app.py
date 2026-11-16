import os
import re
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "adajar_dental.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deployment")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

PROCEDURES = {
    "General and Preventive Care": [
        "Dental exams and cleanings", "Fluoride treatments", "Dental sealants"
    ],
    "Restorative Dentistry": [
        "Fillings", "Crowns", "Root canals", "Bridges"
    ],
    "Cosmetic Dentistry": [
        "Teeth whitening", "Dental bonding", "Veneers", "Tooth shaping"
    ],
    "Oral Surgery": [
        "Tooth extraction", "Dental implants", "Gum grafts", "Dental bone grafts"
    ],
    "Orthodontics": [
        "Braces", "Braces adjustment", "Retainers"
    ],
    "Other Services": [
        "Dentures", "Dental X-rays", "Scaling and root planing", "Airflow"
    ]
}
ALL_PROCEDURES = [item for group in PROCEDURES.values() for item in group]
TIME_SLOTS = [
    ("08:00", "10:00"), ("10:00", "12:00"), ("13:00", "15:00"),
    ("15:00", "17:00")
]

def get_db():
    if "db" not in g:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            procedure TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(appointment_date, time_slot)
        );
    """)
    db.commit()
    db.close()

@app.context_processor
def inject_globals():
    return {"current_user": session.get("user"), "procedures": PROCEDURES, "today": date.today().isoformat()}

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    return render_template("home.html", title="Home")

@app.route("/about")
def about():
    return render_template("about.html", title="About Us")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        contact = request.form.get("contact", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([first, last, contact, email, password, confirm]):
            flash("Please complete all fields.", "danger")
        elif not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{0,49}", first) or not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{0,49}", last):
            flash("Please enter a valid first and last name.", "danger")
        elif not re.fullmatch(r"[0-9+() -]{7,20}", contact):
            flash("Enter a valid contact number.", "danger")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users(first_name,last_name,contact,email,password_hash) VALUES(?,?,?,?,?)",
                    (first, last, contact, email, generate_password_hash(password))
                )
                db.commit()
                flash("Registration successful. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email address is already registered. Please log in instead.", "danger")
    return render_template("register.html", title="Register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["user"] = {"id": user["id"], "first_name": user["first_name"],
                               "last_name": user["last_name"], "email": user["email"]}
            flash(f"Welcome back, {user['first_name']}!", "success")
            destination = request.args.get("next", "")
            if destination.startswith("/") and not destination.startswith("//"):
                return redirect(destination)
            return redirect(url_for("appointment"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", title="Log In")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/appointment", methods=["GET", "POST"])
@login_required
def appointment():
    db = get_db()
    today = date.today().isoformat()
    if request.method == "POST":
        appointment_date = request.form.get("date", "")
        time_slot = request.form.get("time_slot", "")
        procedure = request.form.get("procedure", "").strip()

        try:
            selected_date = date.fromisoformat(appointment_date)
        except ValueError:
            selected_date = None

        valid_slots = [f"{start}-{end}" for start, end in TIME_SLOTS]
        if not selected_date or selected_date < date.today():
            flash("Choose a valid date that is not in the past.", "danger")
        elif selected_date.weekday() == 6:
            flash("The clinic is closed on Sundays. Please choose another date.", "danger")
        elif time_slot not in valid_slots:
            flash("Please choose one of the available time slots.", "danger")
        elif procedure not in ALL_PROCEDURES:
            flash("Please select a valid dental procedure.", "danger")
        else:
            try:
                db.execute(
                    "INSERT INTO appointments(user_id, appointment_date, time_slot, procedure) VALUES(?,?,?,?)",
                    (session["user_id"], appointment_date, time_slot, procedure)
                )
                db.commit()
                flash("Your appointment has been booked successfully.", "success")
                return redirect(url_for("schedule"))
            except sqlite3.IntegrityError:
                db.rollback()
                flash("That date and time are already booked. Please select another slot.", "danger")

    booked = db.execute(
        "SELECT appointment_date, time_slot FROM appointments WHERE appointment_date >= ?",
        (today,)
    ).fetchall()
    booked_slots = [dict(row) for row in booked]
    return render_template("appointment.html", title="Appointment",
                           time_slots=[f"{a}-{b}" for a, b in TIME_SLOTS],
                           booked_slots=booked_slots, today=today)

@app.route("/schedule")
@login_required
def schedule():
    rows = get_db().execute("""
        SELECT a.id, a.appointment_date, a.time_slot, a.procedure, a.status,
               u.first_name, u.last_name
        FROM appointments a JOIN users u ON a.user_id = u.id
        WHERE a.user_id = ?
        ORDER BY a.appointment_date, a.time_slot
    """, (session["user_id"],)).fetchall()
    return render_template("schedule.html", title="My Schedule",
                           appointments=[dict(row) for row in rows])

@app.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    db = get_db()
    row = db.execute(
        "SELECT appointment_date FROM appointments WHERE id=? AND user_id=?",
        (appointment_id, session["user_id"])
    ).fetchone()
    if not row:
        flash("Appointment not found.", "danger")
    elif row["appointment_date"] < date.today().isoformat():
        flash("Past appointments cannot be cancelled.", "danger")
    else:
        db.execute("DELETE FROM appointments WHERE id=? AND user_id=?",
                   (appointment_id, session["user_id"]))
        db.commit()
        flash("Appointment cancelled.", "success")
    return redirect(url_for("schedule"))

@app.route("/api/availability")
@login_required
def availability():
    day = request.args.get("date", "")
    try:
        date.fromisoformat(day)
    except ValueError:
        return {"error": "Invalid date"}, 400
    rows = get_db().execute(
        "SELECT time_slot FROM appointments WHERE appointment_date=?", (day,)
    ).fetchall()
    return {"booked": [row["time_slot"] for row in rows]}

@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html", title="Page Not Found"), 404

@app.errorhandler(500)
def server_error(_error):
    return render_template("500.html", title="Server Error"), 500

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
