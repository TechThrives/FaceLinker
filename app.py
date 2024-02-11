# MODULE IMPORTS

# Flask modules
from flask import Flask, render_template, request, url_for, request, redirect, abort
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_talisman import Talisman
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

# Other modules
from dotenv import load_dotenv
from urllib.parse import urlparse, urljoin
from datetime import datetime
import configparser
import json
import sys
import os

# Local imports
from user import User, Anonymous
from event import Event
from message import Message
from note import Note
from verification import confirm_token


load_dotenv()

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def delete_folder(folder_path):
    try:
        if os.path.exists(folder_path):
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)

                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    delete_folder(item_path)

            os.rmdir(folder_path)
    except Exception as e:
        print(f"Error deleting folder '{folder_path}': {e}")


# Create app
app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT")
# app.config["MONGO_DBNAME"] = "facelinker"
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Create Pymongo
mongo = PyMongo(app)

# Create Bcrypt
bc = Bcrypt(app)

# Create Talisman
csp = {
    "default-src": [
        "'self'",
        "https://code.jquery.com",
        "https://cdnjs.cloudflare.com",
        "https://cdn.jsdelivr.net",
        "'unsafe-inline'",
        "'unsafe-eval'",
    ],
    "img-src": [
        "*",
    ],
    "worker-src": ["blob:"],
}
talisman = Talisman(app, content_security_policy=csp)

# Create CSRF protect
csrf = CSRFProtect()
csrf.init_app(app)

# Create login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"


# ROUTES


# Index
@app.route("/")
def index():
    return render_template("index.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user.is_authenticated:
            # Redirect to index if already authenticated
            return redirect(url_for("dashboard"))
        # Render login page
        return render_template("login.html")

    if request.method == "POST":
        # Retrieve user from database
        users = mongo.db.users
        user_data = users.find_one({"email": request.form["email"]}, {"_id": 0})
        if user_data:
            # Check password hash
            if bc.check_password_hash(user_data["password"], request.form["pass"]):
                # Create user object to login (note password hash not stored in session)
                user = User.make_from_dict(user_data)
                login_user(user)

                # Check for next argument (direct user to protected page they wanted)
                next = request.args.get("next")
                if not is_safe_url(next):
                    return abort(400)

                # Go to profile page after login
                return redirect(next or url_for("dashboard"))

        # Redirect to login page on error
        return render_template(
            "login.html",
            error="Incorrect email address or password. Please try again.",
        )


# Register
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "GET":
        if current_user.is_authenticated:
            # Redirect to index if already authenticated
            return redirect(url_for("dashboard"))
        # Render login page
        return render_template("register.html", error=request.args.get("error"))
    if request.method == "POST":
        # Trim input data
        email = request.form["email"].strip()
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        password = request.form["pass"].strip()

        users = mongo.db.users
        # Check if email address already exists
        existing_user = users.find_one({"email": email}, {"_id": 0})

        if existing_user is None:
            logout_user()
            # Hash password
            hashpass = bc.generate_password_hash(password).decode("utf-8")
            # Create user object (note password hash not stored in session)
            new_user = User(first_name, last_name, email)
            # Create dictionary data to save to database
            user_data_to_save = new_user.dict()
            user_data_to_save["password"] = hashpass

            # Insert user record to database
            if users.insert_one(user_data_to_save):
                return redirect(url_for("login"))
            else:
                # Handle database error
                return render_template(
                    "register.html",
                    error="There was an error. You have not been registered.<br />Please contact support.",
                )

        # Handle duplicate email

        return render_template(
            "register.html",
            error="That email address is already in use. Please login or contact support if you have forgotten your login details.",
        )


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/addevents", methods=["POST", "GET"])
@login_required
def addevents():
    if request.method == "GET":
        return render_template("event_add.html")
    if request.method == "POST":
        # Trim input data
        etitle = request.form["etitle"].strip()
        elocation = request.form["elocation"].strip()
        estart_date = request.form["estart_date"].strip()
        eend_date = request.form["eend_date"].strip()
        edesc = request.form["edesc"].strip()
        events = mongo.db.events
        new_event = Event(etitle, elocation, estart_date, eend_date, edesc)
        event_to_save = new_event.dict()
        inserted_event = events.insert_one(event_to_save)

        users = mongo.db.users
        users.update_one(
            {"id": current_user.id}, {"$push": {"events": inserted_event.inserted_id}}
        )

        return render_template("event_add.html", msg="Event Created Successfully.")


@app.route("/delete_event/<event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    try:
        events = mongo.db.events
        deleted_event = events.find_one_and_delete({"id": event_id})
        users = mongo.db.users
        users.update_one(
            {"id": current_user.id}, {"$pull": {"events": deleted_event["_id"]}}
        )
        delete_folder(
            os.path.join(
                app.config["UPLOAD_FOLDER"], str(current_user.id), str(event_id)
            )
        )
        return redirect(url_for("events"))

    except Exception as e:
        print(f"Error deleting event: {e}")
        return redirect(url_for("events"))


@app.route("/events")
@login_required
def events():
    users = mongo.db.users
    events = users.find_one({"id": current_user.id})
    user_events = mongo.db.users.aggregate(
        [
            {"$match": {"id": current_user.id}},
            {
                "$lookup": {
                    "from": "events",
                    "localField": "events",
                    "foreignField": "_id",
                    "as": "eventDetails",
                }
            },
            {"$project": {"eventDetails._id": 0}},
        ]
    )

    user_events_details = list(user_events)[0]["eventDetails"] if user_events else []
    return render_template("events.html", user_events=user_events_details)


@app.route("/event/<event_id>", methods=["POST", "GET"])
@login_required
def view_event(event_id):
    events = mongo.db.events
    event = events.find_one({"id": event_id})
    event = Event.make_from_dict(event)
    gallery_path = os.path.join(
        app.config["UPLOAD_FOLDER"], str(current_user.id), str(event_id)
    )

    if not os.path.exists(gallery_path):
        return render_template("event_details.html", event=event)

    image_files = [
        "uploads" + "/" + str(current_user.id) + "/" + str(event_id) + "/" + str(f)
        for f in os.listdir(gallery_path)
        if os.path.isfile(os.path.join(gallery_path, f))
    ]

    return render_template("event_details.html", event=event, image_files=image_files)


@app.route("/upload/<event_id>", methods=["GET", "POST"])
@login_required
def event_upload(event_id):
    events = mongo.db.events
    event = events.find_one({"id": event_id})
    event = Event.make_from_dict(event)

    if request.method == "POST":
        directory_path = os.path.join(
            app.config["UPLOAD_FOLDER"], str(current_user.id), str(event_id)
        )

        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

        files = request.files.getlist("files")

        for file in files:
            if file.filename == "":
                continue

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(directory_path, filename)
                file.save(file_path)

            else:
                return render_template(
                    "event_upload.html", event=event, msg="Invalid file format"
                )

        return render_template(
            "event_upload.html", event=event, msg="Files uploaded successfully"
        )

    return render_template("event_upload.html", event=event)


@app.route("/faces")
@login_required
def faces():
    return render_template("faces.html")


# Profile
@app.route("/profile", methods=["GET"])
@login_required
def profile():
    return render_template("profile.html")


# Logout
@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# Change Name
@app.route("/change_name", methods=["POST"])
@login_required
def change_name():
    title = request.form["title"].strip()
    first_name = request.form["first_name"].strip()
    last_name = request.form["last_name"].strip()

    if mongo.db.users.update_one(
        {"email": current_user.email},
        {"$set": {"title": title, "first_name": first_name, "last_name": last_name}},
    ):
        return "User name updated successfully"
    else:
        return "Error! Could not update user name"


# Delete Account
@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user_id = current_user.id

    # Deletion flags
    user_deleted = False
    notes_deleted = False
    messages_deleted = False

    # Delete user details
    if mongo.db.users.delete_one({"id": user_id}):
        user_deleted = True
        logout_user()

    # Delete notes
    if mongo.db.notes.delete_many({"user_id": user_id}):
        notes_deleted = True

    # Delete messages
    if mongo.db.messages.delete_many(
        {"$or": [{"from_id": user_id}, {"to_id": user_id}]}
    ):
        messages_deleted = True

    delete_folder(os.path.join(app.config["UPLOAD_FOLDER"], str(user_id)))
    return {
        "user_deleted": user_deleted,
        "notes_deleted": notes_deleted,
        "messages_deleted": messages_deleted,
    }


# LOGIN MANAGER REQUIREMENTS


# Load user from user ID
@login_manager.user_loader
def load_user(userid):
    # Return user object or none
    users = mongo.db.users
    user = users.find_one({"id": userid}, {"_id": 0})
    if user:
        return User.make_from_dict(user)
    return None


# Safe URL
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


# Heroku environment
# if os.environ.get("APP_LOCATION") == "heroku":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)
# else:
#     app.run(host="localhost", port=8080, debug=True)

if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)
