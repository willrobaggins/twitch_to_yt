import os
import subprocess
import requests

# FILL THESE IN
TWITCH_USERNAME =       "REPLACE WITH USERNAME"
TWITCH_CLIENT_ID =      "REPLACE WITH ID"
TWITCH_OAUTH_TOKEN =    "REPLACE WITH TOKEN" 
STREAMLINK_BIN =        "/path/to/streamlink"

VOD_DIR =               "./vods"
LOG_DIR =               "./logs"
BIN_DIR =               "./bin"
CLIENT_SECRETS =        "./client_secrets.json"
UPLOADED_LOG =          os.path.join(LOG_DIR, "uploaded.log")

os.makedirs(VOD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(BIN_DIR, exist_ok=True)

def already_uploaded(filename):
    if not os.path.exists(UPLOADED_LOG):
        return False
    with open(UPLOADED_LOG, "r") as f:
        return filename.strip() in f.read()

def mark_uploaded(filename):
    with open(UPLOADED_LOG, "a") as f:
        f.write(filename + "\n")

def get_latest_vod_title():
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": TWITCH_OAUTH_TOKEN
    }

    user_url = f"https://api.twitch.tv/helix/users?login={TWITCH_USERNAME}"
    try:
        user_resp = requests.get(user_url, headers=headers)
        user_resp.raise_for_status()
        user_data = user_resp.json()
        if not user_data["data"]:
            print("[ERROR] Could not fetch user ID.")
            return "Untitled Stream", None
        user_id = user_data["data"][0]["id"]
    except Exception as e:
        print(f"[ERROR] Failed to get user ID: {e}")
        return "Untitled Stream", None
    
    vod_url = f"https://api.twitch.tv/helix/videos?user_id={user_id}&first=1&type=archive"
    try:
        vod_resp = requests.get(vod_url, headers=headers)
        vod_resp.raise_for_status()
        vod_data = vod_resp.json()
        if "data" in vod_data and len(vod_data["data"]) > 0:
            video = vod_data["data"][0]
            created_at = video["created_at"][:10]
            date_str = created_at.replace("-", ".")
            title = video["title"]
            vod_id = video["id"]
            return f"[{date_str}] - {title}", vod_id
        else:
            print("[INFO] No archived VODs found.")
            return "Untitled Stream", None
    except Exception as e:
        print(f"[ERROR] Failed to get VOD title: {e}")
        return "Untitled Stream", None

def download_latest_vod(vod_id, filename):
    path = os.path.join(VOD_DIR, filename)
    print(f"[INFO] Downloading VOD {vod_id} to {path}")
    result = subprocess.run([
        STREAMLINK_BIN,
        f"https://www.twitch.tv/videos/{vod_id}",
        "best",
        "-o", path,
        "--twitch-disable-ads"
    ])
    return path if result.returncode == 0 and os.path.exists(path) else None

def upload_to_youtube(path, title):
    print(f"[UPLOAD] Uploading: {os.path.basename(path)} as \"{title}\"")
    result = subprocess.run([
        BIN_DIR,
        "--title", title,
        "--privacy", "unlisted",
        "--client-secrets", CLIENT_SECRETS,
        "--credentials-file", "./yt-oauth.json",
        path
    ])

    if result.returncode == 0:
        mark_uploaded(os.path.basename(path))
    print(f"[DONE] Uploaded and marked: {path}")
    try:
        os.remove(path)
        print(f"[CLEANUP] Deleted local file: {path}")
    except Exception as e:
        print(f"[WARNING] Could not delete {path}: {e}")
    else:
        print(f"[ERROR] Upload failed for: {path}")

title, vod_id = get_latest_vod_title()
filename = f"{TWITCH_USERNAME}_{title.replace(' ', '_')}.mp4"

if not already_uploaded(filename):
    vod_path = download_latest_vod(vod_id, filename)
    if vod_path:
        upload_to_youtube(vod_path, title)
    else:
        print("[SKIP] Download failed.")
else:
    print("[SKIP] Already uploaded.")