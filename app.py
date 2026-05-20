from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os, math
from datetime import datetime

app = Flask(__name__)
app.secret_key = "loaniq123"

DB = os.path.join(os.path.dirname(__file__), "database", "loans.db")

# ── Database setup ────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name   TEXT NOT NULL,
            age         INTEGER,
            email       TEXT,
            phone       TEXT,
            employment  TEXT,
            income      REAL NOT NULL,
            existing_debt REAL DEFAULT 0,
            credit_score  INTEGER NOT NULL,
            loan_amount   REAL NOT NULL,
            loan_purpose  TEXT,
            loan_term     INTEGER DEFAULT 36,
            status        TEXT DEFAULT 'Pending',
            dti_ratio     REAL,
            result_note   TEXT,
            applied_at    TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

# ── Simple rule-based decision (no ML) ───────────────
def make_decision(credit, income, debt, amount, term):
    dti = round((debt / income) * 100, 1) if income > 0 else 100
    lti = round(amount / income, 2)       if income > 0 else 99
    monthly = round(amount / term, 2)     if term > 0 else 0

    # Simple SQL-style rules
    if credit >= 720 and dti < 30 and lti < 2:
        status = "Approved"
        note   = f"Strong profile. Credit score {credit} is excellent. DTI {dti}% is well within safe limit. Eligible for standard rate."
    elif credit >= 650 and dti < 40 and lti < 3:
        status = "Under Review"
        note   = f"Moderate profile. Credit score {credit} is acceptable. DTI {dti}% is within limits. A loan officer will review your application."
    elif credit >= 600 and dti < 50:
        status = "Under Review"
        note   = f"Borderline profile. Credit score {credit} needs improvement. DTI {dti}% is high. Additional documents may be required."
    else:
        status = "Rejected"
        note   = f"High risk profile. Credit score {credit} is below minimum threshold OR DTI {dti}% is too high. Please improve your credit score and reduce existing debt before reapplying."

    return status, note, dti, monthly

# ── Routes ────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/apply", methods=["GET", "POST"])
def apply():
    if request.method == "POST":
        f = request.form
        name     = f.get("full_name", "").strip()
        age      = int(f.get("age") or 0)
        email    = f.get("email", "")
        phone    = f.get("phone", "")
        emp      = f.get("employment", "")
        income   = float(f.get("income") or 0)
        debt     = float(f.get("existing_debt") or 0)
        credit   = int(f.get("credit_score") or 0)
        amount   = float(f.get("loan_amount") or 0)
        purpose  = f.get("loan_purpose", "")
        term     = int(f.get("loan_term") or 36)

        # Basic validation
        if not name:
            flash("Please enter your full name.", "error")
            return render_template("apply.html")
        if credit < 300 or credit > 850:
            flash("Credit score must be between 300 and 850.", "error")
            return render_template("apply.html")
        if income < 1000:
            flash("Annual income must be at least $1,000.", "error")
            return render_template("apply.html")
        if amount < 500:
            flash("Loan amount must be at least $500.", "error")
            return render_template("apply.html")

        status, note, dti, monthly = make_decision(credit, income, debt, amount, term)

        conn = get_db()
        conn.execute("""
            INSERT INTO applications
              (full_name, age, email, phone, employment, income, existing_debt,
               credit_score, loan_amount, loan_purpose, loan_term, status, dti_ratio, result_note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (name, age, email, phone, emp, income, debt, credit, amount, purpose, term, status, dti, note))
        conn.commit()
        app_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.close()

        return redirect(url_for("result", app_id=app_id))

    return render_template("apply.html")

@app.route("/result/<int:app_id>")
def result(app_id):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    conn.close()
    if not app_row:
        return redirect(url_for("home"))
    return render_template("result.html", app=app_row)

@app.route("/dashboard")
def dashboard():
    conn = get_db()
    apps      = conn.execute("SELECT * FROM applications ORDER BY applied_at DESC").fetchall()
    total     = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()["n"]
    approved  = conn.execute("SELECT COUNT(*) AS n FROM applications WHERE status='Approved'").fetchone()["n"]
    rejected  = conn.execute("SELECT COUNT(*) AS n FROM applications WHERE status='Rejected'").fetchone()["n"]
    review    = conn.execute("SELECT COUNT(*) AS n FROM applications WHERE status='Under Review'").fetchone()["n"]
    avg_credit= conn.execute("SELECT ROUND(AVG(credit_score),1) AS v FROM applications").fetchone()["v"] or 0
    avg_dti   = conn.execute("SELECT ROUND(AVG(dti_ratio),1) AS v FROM applications").fetchone()["v"] or 0

    # Purpose breakdown
    purposes  = conn.execute("""
        SELECT loan_purpose, COUNT(*) AS total,
               SUM(CASE WHEN status='Approved' THEN 1 ELSE 0 END) AS approved
        FROM applications GROUP BY loan_purpose
    """).fetchall()

    conn.close()
    rate = round(approved / total * 100, 1) if total else 0
    return render_template("dashboard.html",
        apps=apps, total=total, approved=approved, rejected=rejected,
        review=review, rate=rate, avg_credit=avg_credit, avg_dti=avg_dti,
        purposes=purposes)

@app.route("/application/<int:app_id>")
def view_application(app_id):
    conn = get_db()
    app_row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    conn.close()
    if not app_row:
        return redirect(url_for("dashboard"))
    return render_template("result.html", app=app_row)

if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  LoanIQ Website")
    print("  Open: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True)
