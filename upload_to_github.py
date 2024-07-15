import os
import requests
import json
from dotenv import load_dotenv
import base64
import hashlib

# Load environment variables from the .env file
load_dotenv()

# GitHub configurations
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') or os.getenv('MY_GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

# Google Drive configurations
GOOGLE_DRIVE_FILE_ID = os.getenv('GOOGLE_DRIVE_FILE_ID')

# Print loaded environment variables for debugging
print(f"GITHUB_TOKEN: {GITHUB_TOKEN}")
print(f"GITHUB_REPO: {GITHUB_REPO}")
print(f"GITHUB_BRANCH: {GITHUB_BRANCH}")
print(f"GOOGLE_DRIVE_FILE_ID: {GOOGLE_DRIVE_FILE_ID}")

# Helper function to calculate the SHA-1 hash of a file
def calculate_file_sha1(file_path):
    BUF_SIZE = 65536  # read the file in chunks of 64kb
    sha1 = hashlib.sha1()

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    
    return sha1.hexdigest()

# Function to upload the file to GitHub
def upload_to_github(file_path, repo, branch, token):
    file_name = os.path.basename(file_path)
    url = f"https://api.github.com/repos/{repo}/contents/{file_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Check if the file already exists on GitHub
    response = requests.get(url, headers=headers)
    print(f"GitHub GET response status: {response.status_code}")
    if response.status_code == 200:
        sha = response.json()['sha']
        # Download the existing file to compare
        download_url = response.json()['download_url']
        existing_file_response = requests.get(download_url)
        existing_file_sha1 = hashlib.sha1(existing_file_response.content).hexdigest()
        print(f"Existing file SHA-1: {existing_file_sha1}")
    else:
        sha = None
        existing_file_sha1 = None
    
    # Calculate the SHA-1 of the local file
    local_file_sha1 = calculate_file_sha1(file_path)
    print(f"Local file SHA-1: {local_file_sha1}")
    
    # If the hashes are the same, there is no need to update the file on GitHub
    if existing_file_sha1 == local_file_sha1:
        print(f"The file '{file_name}' is already up to date on GitHub. Upload not necessary.")
        return
    
    with open(file_path, 'rb') as file:
        content = base64.b64encode(file.read()).decode('utf-8')
    
    data = {
        "message": f"Upload {file_name}",
        "content": content,
        "branch": branch
    }
    
    if sha:
        data["sha"] = sha
    
    response = requests.put(url, headers=headers, data=json.dumps(data))
    print(f"GitHub PUT response status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"File '{file_name}' successfully uploaded to GitHub.")
    else:
        print(f"Error uploading file to GitHub: {response.json()}")

try:
    # URL of the CSV file on Google Drive
    download_url = f"https://drive.google.com/uc?export=download&id={GOOGLE_DRIVE_FILE_ID}"
    print(f"Download URL: {download_url}")

    # Download the CSV
    response = requests.get(download_url)
    response.raise_for_status()

    # Fixed name for the file
    file_name = 'data_latest.csv'

    # Save the downloaded file locally as CSV
    local_csv_path = os.path.join(os.getcwd(), file_name)
    with open(local_csv_path, 'wb') as f:
        f.write(response.content)

    print(f"CSV file downloaded and saved to: {local_csv_path}")

    # Upload the CSV file to GitHub
    upload_to_github(local_csv_path, GITHUB_REPO, GITHUB_BRANCH, GITHUB_TOKEN)

except requests.exceptions.RequestException as e:
    print(f"Error downloading the file: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    