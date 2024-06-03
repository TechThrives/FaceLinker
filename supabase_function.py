from supabase import create_client, Client
import numpy as np
import cv2
from PIL import Image
from io import BytesIO

# Initialize the Supabase client
url: str = "https://jgjjxwofpccmpmhnklwl.supabase.co"
key: str = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impnamp4d29mcGNjbXBtaG5rbHdsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTc0MTg2ODMsImV4cCI6MjAzMjk5NDY4M30.n_NMtZ6ol48XLnmB7mQOJyhK1NTsIpp-OvM7u6MvRT4"
)
supabase: Client = create_client(url, key)

bucket_name = "images"


def download_image(file_name):
    response = supabase.storage.from_(bucket_name).download(file_name)
    img = Image.open(BytesIO(response))
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def download_file(local_path, file_path):
    response = supabase.storage.from_(bucket_name).download(file_path)
    with open(local_path, "wb") as f:
        f.write(response)
    return True


def upload_image(image_path, img):
    is_success, buffer = cv2.imencode(".png", img)
    if is_success:
        supabase.storage.from_(bucket_name).upload(
            file=buffer.tobytes(),  # Convert buffer to BytesIO object
            path=image_path,
            file_options={"content-type": "image/png"},
        )


def upload_image_file(image_path, img_bytes, file_ext="png"):
    supabase.storage.from_(bucket_name).upload(
        file=img_bytes,
        path=image_path,
        file_options={"content-type": f"image/{file_ext}"},
    )


def list_images(folder_path):
    response = supabase.storage.from_(bucket_name).list(folder_path)
    return [
        f"{folder_path}/{file['name']}"
        for file in response
        if file["name"].endswith(".png") or file["name"].endswith(".jpg")
    ]


def image_urls(folder_path):
    image_paths = list_images(folder_path)

    url_list = []

    for image_path in image_paths:
        # Get the URL for the specified file path
        response = supabase.storage.from_(bucket_name).get_public_url(image_path)
        url_list.append(response)

    return url_list


def get_url(file_path):
    return supabase.storage.from_(bucket_name).get_public_url(file_path)


def delete_folder(folder_path):
    # Function to list all files and subfolders in the specified folder
    def list_files(bucket, path):
        response = supabase.storage.from_(bucket).list(path)
        files = []
        for file in response:
            full_path = f"{path}/{file['name']}"
            if file["id"] == None:
                # Recursively list files in subfolders
                files.extend(list_files(bucket, full_path))
            else:
                files.append(full_path)
        return files

    # List all files in the folder and its subfolders
    files_to_delete = list_files(bucket_name, folder_path)

    # Delete all listed files
    for file_path in files_to_delete:
        supabase.storage.from_(bucket_name).remove([file_path])

    # Delete the empty folders
    folders_to_delete = list(
        set(
            [
                f"{folder_path}/{file['name']}"
                for file in supabase.storage.from_(bucket_name).list(folder_path)
                if file["id"] == None
            ]
        )
    )
    for folder in folders_to_delete:
        delete_folder(bucket_name, folder)

    # Finally, delete the folder itself if it still exists and is empty
    supabase.storage.from_(bucket_name).remove([folder_path])


def delete_file(file_path):
    supabase.storage.from_(bucket_name).remove(file_path)
