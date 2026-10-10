from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------------------
# Dummy Data
# ---------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

users = [
    {"id": 1, "name": "Pujitha Kollaparthi", "email": "pujitha@example.com", "password": "1234", "role": "User"},
    {"id": 2, "name": "Siva Kumar", "email": "siva@example.com", "password": "1234", "role": "User"},
]

registered_users = users.copy()

jobs = [
    {"id": 1, "title": "Software Developer", "location": "Hyderabad", "experience": "2-4 years"},
    {"id": 2, "title": "Data Analyst", "location": "Bangalore", "experience": "1-3 years"},
    {"id": 3, "title": "UI/UX Designer", "location": "Pune", "experience": "3+ years"},
]

# ---------------------------
# Home Route
# ---------------------------
@app.route("/")
def home():
    return render_template("home.html")

# ---------------------------
# Admin Routes
# ---------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Logged in successfully!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        flash("Please login first", "warning")
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")

@app.route("/admin/view-users")
def view_users():
    if not session.get("admin_logged_in"):
        flash("Please login first", "warning")
        return redirect(url_for("admin_login"))
    return render_template("view_users.html", users=registered_users)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("admin_login"))

# ---------------------------
# User Routes
# ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if email already exists
        for user in registered_users:
            if user["email"] == email:
                flash("Email already registered!", "danger")
                return redirect(url_for("register"))

        registered_users.append({
            "name": name,
            "email": email,
            "password": password,
            "role": "User"
        })
        flash("Registered successfully! Please login.", "success")
        return redirect(url_for("user_login"))
    return render_template("register.html")

@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        for user in registered_users:
            if user["email"] == email and user["password"] == password:
                session["user_logged_in"] = True
                session["user_name"] = user["name"]
                flash("Logged in successfully!", "success")
                return redirect(url_for("user_dashboard"))
        flash("Invalid email or password!", "danger")
        return redirect(url_for("user_login"))
    return render_template("user_login.html")

@app.route("/user/dashboard")
def user_dashboard():
    if not session.get("user_logged_in"):
        flash("Please login first", "warning")
        return redirect(url_for("user_login"))
    return render_template("user_dashboard.html", name=session.get("user_name"))

@app.route("/user/logout")
def user_logout():
    session.pop("user_logged_in", None)
    session.pop("user_name", None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("user_login"))

# ---------------------------
# Job Routes
# ---------------------------
@app.route("/jobs")
def job_list():
    return render_template("job.html", jobs=jobs)

@app.route("/job/<int:job_id>")
def job_detail(job_id):
    job = next((job for job in jobs if job["id"] == job_id), None)
    if not job:
        flash("Job not found!", "danger")
        return redirect(url_for("job_list"))
    return render_template("job_detail.html", job=job)

# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
