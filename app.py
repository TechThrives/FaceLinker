# MODULE IMPORTS

# Flask modules
from flask import (
    Flask,
    render_template,
    send_file,
    request,
    url_for,
    request,
    redirect,
    abort,
    jsonify,
)
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
import uuid
import os

# Local imports
from user import User, Anonymous
from event import Event
from face import Face
from utils import remove_files_from_folder, download_create_zip
from deepface_function import extract_faces_and_compare, update_faces_collection
from supabase_function import (
    upload_image_file,
    image_urls,
    get_url,
    delete_folder,
    delete_file,
)

load_dotenv()

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
        "https://cdn.tailwindcss.com",
        "'unsafe-inline'",
        "'unsafe-eval'",
    ],
    "img-src": ["*", "worker-src blob:", "data:"],
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


# Define a context processor function
@app.context_processor
def utility_processor():
    def get_events():
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
                {"$unwind": "$eventDetails"},
                {
                    "$lookup": {
                        "from": "faces",
                        "localField": "eventDetails.faces",
                        "foreignField": "_id",
                        "as": "eventDetails.faces",
                    }
                },
                {"$group": {"_id": "$_id", "eventDetails": {"$push": "$eventDetails"}}},
                {"$project": {"_id": 0}},
            ]
        )
        all_event = list(user_events)
        user_events_details = all_event[0]["eventDetails"] if len(all_event) else []
        for event in user_events_details:
            event_id = event['id']
            for face in event['faces']:
                face_id = face['id']
                face['image_path'] = get_url("{}/{}/faces/{}.png"
                .format(current_user.id, event_id, face_id))
        return user_events_details

    def get_user():
        user = mongo.db.users.find_one({"id": current_user.id}, {"_id": 0})
        profile = User.make_from_dict(user)
        profile.profile_image = get_url(profile.profile_image)
        return profile

    return dict(get_events=get_events, get_user=get_user)


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


@app.route("/add_event", methods=["POST", "GET"])
@login_required
def add_event():
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

        event_path = f"{str(current_user.id)}/{str(event_id)}"
        delete_folder(event_path)

        faces = mongo.db.faces
        face_ids = deleted_event["faces"]
        for face_id in face_ids:
            faces.find_one_and_delete({"_id": face_id})

        return redirect(url_for("events"))

    except Exception as e:
        print(f"Error deleting event: {e}")
        return redirect(url_for("events"))


@app.route("/events")
@login_required
def events():
    return render_template("events.html")


@app.route("/event/<event_id>", methods=["POST", "GET"])
@login_required
def view_event(event_id):
    events = mongo.db.events
    event = events.find_one({"id": event_id})
    if event:
        event = Event.make_from_dict(event)
        gallery_path = f"{str(current_user.id)}/{str(event_id)}"

        image_files = image_urls(gallery_path)

        return render_template(
            "event_details.html", event=event, image_files=image_files
        )

    return redirect(url_for("dashboard"))


@app.route("/upload/<event_id>", methods=["GET", "POST"])
@login_required
def event_upload(event_id):
    events = mongo.db.events
    event = events.find_one({"id": event_id})
    if event:
        event = Event.make_from_dict(event)

        if request.method == "POST":
            event_path = f"{str(current_user.id)}/{str(event_id)}"

            facelib_path = f"{str(current_user.id)}/{str(event_id)}/faces"

            files = request.files.getlist("files")

            for file in files:
                if file.filename == "":
                    continue

                if file and allowed_file(file.filename):
                    file_ext = file.filename.rsplit(".", 1)[1].lower()
                    file_id = str(uuid.uuid4())
                    img_bytes = file.read()
                    # filename = secure_filename(file.filename)
                    img_id = file_id + "." + file_ext
                    img_path = f"{event_path}/{img_id}"
                    results = extract_faces_and_compare(img_bytes, img_id, facelib_path)
                    update_faces_collection(mongo, results, event_id)
                    upload_image_file(img_path, img_bytes, file_ext)

                else:
                    return render_template(
                        "event_upload.html", event=event, msg="Invalid file format"
                    )

            return render_template(
                "event_upload.html", event=event, msg="Files uploaded successfully"
            )

        return render_template("event_upload.html", event=event)

    return redirect(url_for("dashboard"))


@app.route("/faces/<event_id>")
@login_required
def faces(event_id):
    faces = mongo.db.faces
    events = mongo.db.events
    event = events.find_one({"id": event_id})
    if event:
        event = Event.make_from_dict(event)

        image_files = {}

        face_object = faces.find({"event_id": event_id})
        face_object = list(face_object)

        image_files = [
            {
                "image_path": get_url(
                    "{}/{}/faces/{}.png".format(current_user.id, event_id, face.id)
                ),
                "face_obj": face,
            }
            for face in [Face.make_from_dict(face) for face in face_object]
        ]

        return render_template("faces.html", image_files=image_files, event=event)

    return redirect(url_for("dashboard"))


@app.route("/face/<face_id>", methods=["GET"])
@login_required
def view_face(face_id):
    faces = mongo.db.faces
    face = faces.find_one({"id": face_id})
    if face:
        face = Face.make_from_dict(face)

        # Prepare image_files for the current face
        image_files = []

        # For each image, query for other faces in the same image
        for image in face.images:
            img_id = image["img_id"]
            
            # Find other faces in the same image
            other_faces = faces.find({
                "images": {"$elemMatch": {"img_id": img_id}},
                "id": {"$ne": face_id}  # Exclude the current face
            })

            # Process other faces
            other_faces_list = []
            for other_face in other_faces:
                # Construct face_data for each other face
                for other_image in other_face['images']:
                    if other_image['img_id'] == img_id:
                        face_data = {
                            'id': other_face['id'],
                            'name': other_face['name'],
                            'face_location': other_image['face_location']
                        }
                        other_faces_list.append(face_data)
                        break  # To avoid duplicate entries

            # Append image file entry with other faces
            image_files.append({
                "image_path": get_url("{}/{}/{}".format(current_user.id, face.event_id, img_id)),
                "face": {
                            'id': face.id,
                            'name': face.name,
                            'face_location': image['face_location']
                        },
                "other_faces": other_faces_list
            })

        return render_template("face_details.html", face=face, image_files=image_files)

    return redirect(url_for("dashboard"))


@app.route("/update_name", methods=["POST"])
def update_name():
    new_name = request.form["name"]
    face_id = request.form["face_id"]

    # Save the updated face document back to the database
    if mongo.db.faces.update_one({"id": face_id}, {"$set": {"name": new_name}}):
        return jsonify({"status": "success", "message": "Name updated successfully"})
    else:
        return jsonify({"status": "error", "message": "Face not found"})


# download images
@app.route("/download/<face_id>", methods=["GET"])
@login_required
def face_download(face_id):
    faces = mongo.db.faces
    face = faces.find_one({"id": face_id})
    if face:
        face = Face.make_from_dict(face)

        files_to_zip = []
        for image in face.images:
            files_to_zip.append(
                f"{str(current_user.id)}/{str(face.event_id)}/{image['img_id']}"
            )

        zip_name = "{}.zip".format(face.id)

        download_path = os.path.join("static", "downloads")
        os.makedirs(download_path, exist_ok=True)

        zip_file = os.path.join(download_path, zip_name)

        remove_files_from_folder(download_path)

        download_create_zip(download_path, files_to_zip, zip_file)

        return send_file(zip_file, as_attachment=True)


# Profile
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    users = mongo.db.users
    user = users.find_one({"id": current_user.id})
    profile = User.make_from_dict(user)
    profile.profile_image = get_url(profile.profile_image)

    if request.method == "POST":

        profile_img_path = f"{str(current_user.id)}"

        file = request.files["profileImage"]

        if file and file.filename != "" and allowed_file(file.filename):
            img_bytes = file.read()
            img_id = str(current_user.id) + ".png"
            img_path = f"{profile_img_path}/{img_id}"
            delete_file(img_path)
            upload_image_file(img_path, img_bytes)

            users.update_one(
                {"id": current_user.id},
                {
                    "$set": {
                        "profile_image": img_path,
                    }
                },
            )

        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()

        if first_name != "" and last_name != "":
            users.update_one(
                {"id": current_user.id},
                {
                    "$set": {
                        "first_name": first_name,
                        "last_name": last_name,
                    }
                },
            )
        else:
            return render_template(
                "profile.html",
                profile=profile,
                msg="First Name and Last Name Must Not Empty.",
            )

        password = request.form["password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        if password != "" or confirm_password != "":
            if password == confirm_password:
                hashpass = bc.generate_password_hash(password).decode("utf-8")
                users.update_one(
                    {"id": current_user.id},
                    {
                        "$set": {
                            "password": hashpass,
                        }
                    },
                )
            else:
                return render_template(
                    "profile.html",
                    profile=profile,
                    msg="Password and Confirm Password Not Match.",
                )

        user = users.find_one({"id": current_user.id})
        profile = User.make_from_dict(user)
        profile.profile_image = get_url(profile.profile_image)

        return render_template(
            "profile.html",
            profile=profile,
            msg="Profile Updated Successfully.",
        )

    return render_template("profile.html", profile=profile)


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
