import requests
import os
import concurrent.futures
from datetime import datetime

# --- Configuration ---
API_KEY = 'Your immich api key'
BASE_URL = 'http://Your-immich-server-address/api'
# Number of concurrent uploads. Adjust based on your machine and network.
# Good values are between 5 and 15.
MAX_WORKERS = 10

# List of common photo and video extensions to upload.
SUPPORTED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif',
    '.mov', '.mp4', '.m4v', '.3gp', '.avi', '.mkv', '.wmv', '.mpg'
}

def upload_file(file_path):
    """Uploads a single file to the Immich server and returns the result."""
    basename = os.path.basename(file_path)
    try:
        # Get file creation and modification times
        stats = os.stat(file_path)
        file_created_at = datetime.fromtimestamp(stats.st_ctime).isoformat()
        file_modified_at = datetime.fromtimestamp(stats.st_mtime).isoformat()

        # Generate a unique ID for the asset on the device to aid the server
        device_asset_id = f'{basename}-{stats.st_mtime}'

        headers = {
            'Accept': 'application/json',
            'x-api-key': API_KEY,
        }
        
        data = {
            'deviceAssetId': device_asset_id,
            'deviceId': 'python-multithread-uploader',
            'fileCreatedAt': file_created_at,
            'fileModifiedAt': file_modified_at,
            'isFavorite': 'false',
        }
        
        with open(file_path, 'rb') as f:
            files = {'assetData': (basename, f)}
            response = requests.post(f'{BASE_URL}/assets', headers=headers, data=data, files=files, timeout=30)
        
        # Raise an exception for HTTP errors (e.g., 401 Unauthorized, 500 Server Error)
        response.raise_for_status()
        
        response_json = response.json()
        
        # Immich API returns a 'duplicate' key in the response if the file exists
        if response_json.get('duplicate'):
            return f"SKIPPED (Duplicate): {basename}"
        else:
            return f"SUCCESS: Uploaded {basename} (ID: {response_json.get('id')})"
            
    except requests.exceptions.HTTPError as errh:
        return f"HTTP Error for {basename}: {errh} | Response: {response.text}"
    except requests.exceptions.RequestException as err:
        return f"Request Exception for {basename}: {err}"
    except IOError as e:
        return f"File Error for {file_path}: {e}"

def scan_and_upload_directory(root_directory):
    """Recursively scans a directory and uploads all supported media files using multiple threads."""
    if not os.path.isdir(root_directory):
        print(f"Error: Directory not found at '{root_directory}'")
        return
    
    print("Scanning for media files, please wait...")
    
    files_to_upload = []
    # os.walk will traverse the directory tree for us
    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            # Check if the file has one of the supported extensions
            _, extension = os.path.splitext(filename)
            if extension.lower() in SUPPORTED_EXTENSIONS:
                files_to_upload.append(os.path.join(dirpath, filename))

    if not files_to_upload:
        print("No media files found to upload.")
        return

    print(f"Found {len(files_to_upload)} media files. Starting multithreaded upload with {MAX_WORKERS} workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # The 'map' function applies 'upload_file' to every item in 'files_to_upload'
        # and returns the results as they are completed.
        results = executor.map(upload_file, files_to_upload)
        
        # Print results as they come in
        for result in results:
            print(result)
            
    print("\nUpload process complete.")

if __name__ == '__main__':
    if API_KEY == 'YOUR_API_KEY' or BASE_URL == 'http://your-immich-instance.com/api':
        print("Error: Please configure your API_KEY and BASE_URL in the script before running.")
    else:
        media_directory = input("Enter the path to your 'Photos' takeout directory: ")
        scan_and_upload_directory(media_directory)