from flask import Flask, request, jsonify, render_template, redirect, url_for, session

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "dev-secret-change-me"  # lab only


@app.get("/")
def index():
    if request.cookies.get("token"):
        return render_template("index.html")
    return redirect("/login")


# --- Login page (GET) ---
@app.get("/login")
def login_page():
    # If redirected with an error message, it will be passed as query arg ?err=...
    err = request.args.get("err")
    return render_template("login.html", error=err)


# --- Login handler (POST) ---
@app.post("/login")
def login_post():
    # Accept JSON or classic form
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    # super simple lab creds
    ok = username == "admin" and password == "admin"

    # If client asked for JSON (AJAX), respond JSON
    wants_json = request.is_json or request.headers.get("Accept", "").startswith(
        "application/json"
    )

    if ok:
        session["user"] = username
        if wants_json:
            return jsonify({"ok": True, "msg": "welcome"}), 200
        return redirect(url_for("admin_page"))

    # wrong creds
    if wants_json:
        return jsonify({"ok": False, "msg": "invalid credentials"}), 401
    # Render page again with an inline error
    return render_template("login.html", error="Invalid credentials"), 401


# --- Admin page (GET, protected) ---
@app.get("/admin")
def admin_page():
    if "user" not in session:
        # send them back with a friendly message
        return redirect(url_for("login_page", err="Please sign in to access admin"))
    return render_template("admin.html", user=session["user"])


# --- Logout (optional) ---
@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))
