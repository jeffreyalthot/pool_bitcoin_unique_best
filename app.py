from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

from config import DATABASE_PATH, SECRET_KEY
from rpc import BitcoinRPCError, call_rpc

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.commit()


@app.before_request
def ensure_db():
    init_db()


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            error = "Username and password are required."
        else:
            password_hash = generate_password_hash(password)
            try:
                with get_db() as connection:
                    connection.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, password_hash),
                    )
                    connection.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username already exists."
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid credentials."
        else:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    rpc_status = "Disconnected"
    info = None
    try:
        info = call_rpc("getblockchaininfo")
        rpc_status = "Connected"
    except BitcoinRPCError:
        rpc_status = "RPC error"
    return render_template(
        "dashboard.html",
        username=session.get("username"),
        rpc_status=rpc_status,
        info=info,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
