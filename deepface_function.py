import cv2
from deepface import DeepFace
import uuid
import os


def face_compare(src_img, facelib_path):

    all_files = os.listdir(facelib_path)

    image_files = [file for file in all_files if file.lower().endswith((".png"))]

    for image_file in image_files:
        image_file_path = os.path.join(facelib_path, image_file)

        exist = DeepFace.verify(src_img, image_file_path)["verified"]
        if exist:
            img_id = image_file.split(".")[0]
            return True, img_id
        else:
            continue
    img_id = uuid.uuid4().hex[:10]
    img_path = str(f"{facelib_path}{img_id}.png")
    cv2.imwrite(img_path, src_img)
    return False, img_id


def extract_faces_and_compare(img_path, img_id, facelib_path):

    face_objs = DeepFace.extract_faces(img_path=img_path)
    results = []

    for i, face_obj in enumerate(face_objs):
        img = cv2.imread(img_path)
        roi = img[
            face_obj["facial_area"]["y"] : face_obj["facial_area"]["y"]
            + face_obj["facial_area"]["h"],
            face_obj["facial_area"]["x"] : face_obj["facial_area"]["x"]
            + face_obj["facial_area"]["w"],
        ]
        exist, id = face_compare(roi, facelib_path)
        results.append(
            {
                "exist": exist,
                "id": id,
                "img_id": img_id,
                "face_location": [
                    face_obj["facial_area"]["x"],
                    face_obj["facial_area"]["y"],
                    face_obj["facial_area"]["w"],
                    face_obj["facial_area"]["h"],
                ],
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
                {"id": face_id}, {"$push": {"images": [img_id, face_location]}}
            )
        else:
            new_face = {
                "id": face_id,
                "event_id": event_id,
                "name": "unknown",
                "images": [[img_id, face_location]],
            }
            inserted_face = faces.insert_one(new_face)

            events = mongo.db.events
            events.update_one(
                {"id": event_id}, {"$push": {"faces": inserted_face.inserted_id}}
            )
