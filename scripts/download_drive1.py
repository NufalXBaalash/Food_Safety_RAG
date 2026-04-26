import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from tqdm import tqdm

# Setup paths relative to the script location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

# Drive manifest paths per country
_DRIVE_MANIFESTS = {
    "egypt":  os.path.join(BASE_DIR, "data", "raw", "drive_files.json"),
    "saudi":  os.path.join(BASE_DIR, "data", "raw", "saudi", "saudi_drive_files.json"),
}

def _get_manifest_path(country: str) -> str:
    """Return the drive manifest JSON path for the given country."""
    return _DRIVE_MANIFESTS.get(country, _DRIVE_MANIFESTS["egypt"])


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


def download_cluster_data(cluster_name: str, country: str = "egypt") -> bool:
    """
    Download all files for *cluster_name* from Google Drive.

    Args:
        cluster_name: Folder/cluster name as it appears in the manifest JSON.
        country:      'egypt' or 'saudi'. Controls which manifest file is used.

    Returns:
        True on success, False if the cluster was not found or URL is empty.
    """
    import logging
    log = logging.getLogger(__name__)

    manifest_path = _get_manifest_path(country)

    if not os.path.exists(manifest_path):
        log.warning(f"Drive manifest missing for country='{country}': {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_lib = None
    for lib in data.get("libraries", []):
        if lib.get("name") == cluster_name:
            target_lib = lib
            break

    if not target_lib:
        log.warning(f"Cluster '{cluster_name}' not found in {manifest_path}")
        return False

    cluster_url = target_lib.get("url", "").strip()
    if not cluster_url:
        log.warning(
            f"  [DOWNLOAD] No Drive URL for Saudi cluster '{cluster_name}'. "
            f"Edit data/raw/saudi/saudi_drive_files.json to add the folder link."
        )
        return False

    log.info(f"Authenticating PyDrive2 to download '{cluster_name}' ({country})...")
    drive = authenticate()

    # Determine save path: clusters always go into data/raw/<country>/<name>/
    save_path = os.path.join(RAW_DATA_DIR, country, cluster_name)

    os.makedirs(save_path, exist_ok=True)

    metadata_path = os.path.join(save_path, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as meta_f:
        json.dump(target_lib, meta_f, ensure_ascii=False, indent=4)

    log.info(f"Downloading files for cluster: {cluster_name}")
    folder_id = extract_folder_id(cluster_url)
    download_folder(drive, folder_id, save_path)
    return True

if __name__ == "__main__":
    print("This script is now managed natively by run_pipeline.py (Stage 0).")