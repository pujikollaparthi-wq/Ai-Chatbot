from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "secret_key"

# Database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------- USER MODEL -------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    skills = db.Column(db.Text)


# ------------------- JOB MODEL -------------------
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    company = db.Column(db.String(100))


# ------------------- HOME PAGE -------------------
@app.route("/")
def home():
    return render_template("home.html")


# ------------------- REGISTER -------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        skills = request.form["skills"]

        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect("/register")

        new_user = User(name=name, email=email, password=password, skills=skills)

        db.session.add(new_user)
        db.session.commit()

        flash("Registration Successful! Please Login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------- LOGIN -------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            session["user_id"] = user.id
            return redirect(url_for("dashboard", user_id=user.id))
        else:
            flash("Invalid email or password!", "danger")
            return redirect("/login")

    return render_template("login.html")


# ------------------- DASHBOARD -------------------
@app.route("/dashboard/<int:user_id>")
def dashboard(user_id):
    user = User.query.get(user_id)
    return render_template("dashboard.html", user=user)


# ------------------- JOB PAGE -------------------
@app.route("/jobs/<int:id>")
def jobs(id):
    job = Job.query.get(id)

    if job is None:
        return "Job Not Found", 404

    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])

    return render_template("jobs.html", job=job, user=user)


# ------------------- RUN APP -------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
