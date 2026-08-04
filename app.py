import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_PATH = "quiz.db"

QUESTIONS = [
    {"q": "Bharat ki rajdhani kya hai?", "options": ["Mumbai", "Delhi", "Kolkata", "Chennai"], "answer": "Delhi"},
    {"q": "2 + 2 * 2 = ?", "options": ["6", "8", "4", "10"], "answer": "6"},
    {"q": "Sabse bada grah kaunsa hai?", "options": ["Mars", "Earth", "Jupiter", "Venus"], "answer": "Jupiter"},
    {"q": "Python kis type ki language hai?", "options": ["Compiled", "Interpreted", "Assembly", "Machine"], "answer": "Interpreted"},
    {"q": "HTML ka full form kya hai?", "options": ["HyperText Markup Language", "High Text Machine Language", "HyperTransfer Markup Language", "None"], "answer": "HyperText Markup Language"},
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            best_score INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            return render_template("register.html", error="Sabhi field zaroori hain.")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            return render_template("register.html", error="Ye username pehle se hai.")

        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Galat username ya password.")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html", username=session["username"], total_questions=len(QUESTIONS))


@app.route("/quiz")
@login_required
def quiz():
    session["score"] = 0
    session["q_index"] = 0
    return redirect(url_for("question"))


@app.route("/question", methods=["GET", "POST"])
@login_required
def question():
    q_index = session.get("q_index", 0)

    if request.method == "POST":
        selected = request.form.get("option")
        correct_answer = QUESTIONS[q_index]["answer"]
        if selected == correct_answer:
            session["score"] = session.get("score", 0) + 1
        q_index += 1
        session["q_index"] = q_index

    if q_index >= len(QUESTIONS):
        final_score = session.get("score", 0)

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if final_score > user["best_score"]:
            conn.execute("UPDATE users SET best_score = ? WHERE id = ?", (final_score, session["user_id"]))
            conn.commit()
        conn.close()

        return render_template("result.html", score=final_score, total=len(QUESTIONS))

    current_q = QUESTIONS[q_index]
    return render_template(
        "question.html",
        question=current_q["q"],
        options=current_q["options"],
        q_number=q_index + 1,
        total=len(QUESTIONS),
    )


@app.route("/leaderboard")
@login_required
def leaderboard():
    conn = get_db()
    top_users = conn.execute(
        "SELECT username, best_score FROM users ORDER BY best_score DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return render_template("leaderboard.html", top_users=top_users)


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
