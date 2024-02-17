import os


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
                # print(f"Removed: {file_path}")
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
