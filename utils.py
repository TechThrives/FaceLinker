import os
import zipfile
from supabase_function import download_file


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


def remove_files_from_folder(folder_path):
    files = os.listdir(folder_path)

    for file in files:
        file_path = os.path.join(folder_path, file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error removing {file_path}: {e}")


def delete_file(file_path):
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except Exception as ex:
        print(f"Error removing {file_path}: {ex}")


def create_zip(file_list, zip_file):
    with zipfile.ZipFile(zip_file, "w") as zipf:
        for file in file_list:
            zipf.write(file, os.path.basename(file))


def download_create_zip(download_folder, file_list, zip_file):
    with zipfile.ZipFile(zip_file, "w") as zipf:
        for file in file_list:
            temp_file = os.path.join(download_folder, file.split("/")[-1])
            if download_file(temp_file, file):
                zipf.write(temp_file, os.path.basename(temp_file))
