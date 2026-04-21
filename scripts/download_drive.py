import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from tqdm import tqdm

# Setup paths relative to the script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
DRIVE_FILES_JSON_PATH = os.path.join(BASE_DIR, "data", "raw", "drive_files.json")
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")


def authenticate():
    # Force PyDrive2 to request offline access so it gets a refresh token
    GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = CREDENTIALS_PATH
    GoogleAuth.DEFAULT_SETTINGS['get_refresh_token'] = True
    GoogleAuth.DEFAULT_SETTINGS['oauth_scope'] = ['https://www.googleapis.com/auth/drive.readonly']
    
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile(CREDENTIALS_PATH)
    
    token_file = os.path.join(BASE_DIR, "token.json")
    gauth.LoadCredentialsFile(token_file)
    
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        try:
            gauth.Refresh()
        except Exception:
            # If refresh fails (e.g., no refresh token saved previously), force re-auth
            gauth.LocalWebserverAuth()
    else:
        gauth.Authorize()
        
    gauth.SaveCredentialsFile(token_file)
    return GoogleDrive(gauth)


def extract_folder_id(url: str):
    return url.split("folders/")[-1].split("?")[0]


def download_folder(drive, folder_id, save_path):
    os.makedirs(save_path, exist_ok=True)

    file_list = drive.ListFile(
        {'q': f"'{folder_id}' in parents and trashed=false"}
    ).GetList()

    for file in tqdm(file_list, desc=f"Downloading into {os.path.basename(save_path)}"):
        file_name = file['title']
        file_id = file['id']
        mime_type = file['mimeType']

        # If it is a subfolder, recurse into it
        if mime_type == 'application/vnd.google-apps.folder':
            subfolder_path = os.path.join(save_path, file_name)
            download_folder(drive, file_id, subfolder_path)
        else:
            file_path = os.path.join(save_path, file_name)

            # Skip if file already exists to resume interrupted downloads easily
            if os.path.exists(file_path):
                continue
                
            try:
                file.GetContentFile(file_path)
            except Exception as e:
                print(f"Error downloading {file_name}: {e}")


def main():
    print("Authenticating with Google Drive...")
    drive = authenticate()

    print(f"Reading target files from {DRIVE_FILES_JSON_PATH}")
    with open(DRIVE_FILES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    libraries = data.get("libraries", [])

    for lib in libraries:
        lib_name = lib.get("name")
        lib_url = lib.get("url")

        if not lib_name or not lib_url:
            print(f"Skipping invalid library entry: {lib}")
            continue

        folder_id = extract_folder_id(lib_url)
        save_path = os.path.join(RAW_DATA_DIR, lib_name)

        # Create the specific folder for the library data
        os.makedirs(save_path, exist_ok=True)
        
        # Save specific metadata JSON inside the folder
        metadata_path = os.path.join(save_path, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as meta_f:
            json.dump(lib, meta_f, ensure_ascii=False, indent=4)

        print(f"\n Processing Library: {lib_name}")
        download_folder(drive, folder_id, save_path)


if __name__ == "__main__":
    main()