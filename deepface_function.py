import cv2
from deepface import DeepFace
import uuid
import os

import numpy as np
from supabase_function import download_image, list_images, upload_image


def face_compare(src_img, folder_path):
    image_files = list_images(folder_path)
    for image_file in image_files:
        target_img = download_image(image_file)
        exist = DeepFace.verify(src_img, target_img, enforce_detection=False, model_name="ArcFace")[
            "verified"
        ]
        if exist:
            img_id = os.path.basename(image_file).split(".")[0]
            return True, img_id

    img_id = uuid.uuid4().hex[:10]
    img_path = f"{folder_path}/{img_id}.png"
    upload_image(img_path, src_img)
    return False, img_id


def extract_faces_and_compare(img_bytes, img_name, folder_path):
    # Extract faces
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    face_objs = DeepFace.extract_faces(img_path=img, enforce_detection=False)
    results = []

    for i, face_obj in enumerate(face_objs):
        if face_obj["confidence"] < 0.5:
            continue
        roi = img[
            face_obj["facial_area"]["y"] : face_obj["facial_area"]["y"]
            + face_obj["facial_area"]["h"],
            face_obj["facial_area"]["x"] : face_obj["facial_area"]["x"]
            + face_obj["facial_area"]["w"],
        ]

        exist, id = face_compare(roi, folder_path)
        results.append(
            {
                "exist": exist,
                "id": id,
                "img_id": img_name,
                "face_location": {
                    "x":face_obj["facial_area"]["x"],
                    "y":face_obj["facial_area"]["y"],
                    "w":face_obj["facial_area"]["w"],
                    "h":face_obj["facial_area"]["h"],
                },
            }
        )

    return results


def update_faces_collection(mongo, results, event_id):

    faces = mongo.db.faces
    for result in results:

        face_id = result["id"]
        img_id = result["img_id"]
        face_location = result["face_location"]
        exist = result["exist"]

        if exist:
            faces.update_one(
                {"id": face_id}, {"$push": {"images": {"img_id": img_id, "face_location": face_location}}}
            )
        else:
            new_face = {
                "id": face_id,
                "event_id": event_id,
                "name": "unknown",
                "images": [{"img_id": img_id, "face_location": face_location}],
            }
            inserted_face = faces.insert_one(new_face)

            events = mongo.db.events
            events.update_one(
                {"id": event_id}, {"$push": {"faces": inserted_face.inserted_id}}
            )
