from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

from config import DATABASE_PATH, SECRET_KEY, STRATUM_PUBLIC_URL
from rpc import BitcoinRPCError, call_rpc

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


@app.context_processor
def inject_pool_config():
    return {"stratum_public_url": STRATUM_PUBLIC_URL}


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
                password_hash TEXT NOT NULL,
                pool_username TEXT UNIQUE NOT NULL,
                pool_password TEXT NOT NULL DEFAULT 'x'
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "pool_username" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN pool_username TEXT UNIQUE"
            )
        if "pool_password" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN pool_password TEXT NOT NULL DEFAULT 'x'"
            )
        connection.execute(
            """
            UPDATE users
            SET pool_username = COALESCE(pool_username, username),
                pool_password = COALESCE(pool_password, 'x')
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
            pool_username = username
            pool_password = "x"
            try:
                with get_db() as connection:
                    connection.execute(
                        """
                        INSERT INTO users (username, password_hash, pool_username, pool_password)
                        VALUES (?, ?, ?, ?)
                        """,
                        (username, password_hash, pool_username, pool_password),
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
    pool_username = None
    pool_password = None
    try:
        info = call_rpc("getblockchaininfo")
        rpc_status = "Connected"
    except BitcoinRPCError:
        rpc_status = "RPC error"
    with get_db() as connection:
        user = connection.execute(
            "SELECT pool_username, pool_password FROM users WHERE id = ?",
            (session.get("user_id"),),
        ).fetchone()
        if user:
            pool_username = user["pool_username"]
            pool_password = user["pool_password"]
    return render_template(
        "dashboard.html",
        username=session.get("username"),
        pool_username=pool_username,
        pool_password=pool_password,
        rpc_status=rpc_status,
        info=info,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
