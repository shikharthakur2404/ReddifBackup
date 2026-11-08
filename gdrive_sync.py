#!/usr/bin/env python3
"""
Google Drive Cloud Sync & Automation Module for Rediffmail Backup Suite
======================================================================
Targets: Uploads, mirrors, and auto-shares backup vaults with Pushkar (phsnoida@gmail.com).
Protocols: Google Drive API v3 (Resumable Upload, Idempotent Delta Sync)
"""

import os
import sys
import time
import argparse
import zipfile
from pathlib import Path
from datetime import datetime

# Google Drive Client Libraries
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    GDRIVE_LIBS_AVAILABLE = True
except ImportError:
    GDRIVE_LIBS_AVAILABLE = False

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

DEFAULT_TARGET_EMAIL = "phsnoida@gmail.com"
DEFAULT_ROOT_FOLDER_NAME = "ReddiffBackup_Vault"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_drive_service(creds_path: str = CREDENTIALS_FILE, token_path: str = TOKEN_FILE):
    """
    Authenticate and return Google Drive v3 service instance.
    Supports OAuth2 (InstalledAppFlow) and Service Account credentials.
    """
    if not GDRIVE_LIBS_AVAILABLE:
        print("[!] Google Drive libraries missing. Run: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    creds = None
    creds_p = Path(creds_path).resolve()
    token_p = Path(token_path).resolve()

    # 1. Check for Service Account Key
    if creds_p.exists():
        try:
            creds = service_account.Credentials.from_service_account_file(
                str(creds_p), scopes=SCOPES
            )
            print("[+] Authenticated using Google Service Account.")
            return build("drive", "v3", credentials=creds)
        except Exception:
            # Fall through to OAuth2 flow
            pass

    # 2. Check for existing OAuth2 Token
    if token_p.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_p), SCOPES)
        except Exception:
            creds = None

    # 3. Refresh or Request New OAuth2 Token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[*] Refreshing expired OAuth token...")
            creds.refresh(Request())
        else:
            if not creds_p.exists():
                print(f"\n[!] Missing '{creds_path}'.")
                print("    To authenticate Google Drive:")
                print("    1. Go to Google Cloud Console (console.cloud.google.com)")
                print("    2. Enable Google Drive API")
                print("    3. Create OAuth 2.0 Client ID (Desktop Application)")
                print(f"    4. Download JSON and save as '{creds_path}' in this directory.")
                print(f"    Alternatively, Pushkar can run the script with his account.\n")
                sys.exit(1)

            print("[*] Launching browser OAuth authorization flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_p), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save authorized credentials for future headless runs
        with open(token_p, "w") as token_file:
            token_file.write(creds.to_json())
        print(f"[+] Token stored in {token_path}")

    return build("drive", "v3", credentials=creds)


def find_or_create_folder(service, folder_name: str, parent_id: str = None) -> str:
    """Find an existing folder by name under parent or create it."""
    query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"

    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create folder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")


def share_folder(service, folder_id: str, email_address: str, role: str = "writer"):
    """Grant permissions on the Google Drive folder to target email."""
    if not email_address:
        return
    try:
        # Check existing permissions
        existing = service.permissions().list(fileId=folder_id, fields="permissions(emailAddress, role)").execute()
        for perm in existing.get("permissions", []):
            if perm.get("emailAddress", "").lower() == email_address.lower():
                print(f"[*] Access already granted to: {email_address} ({perm.get('role')})")
                return

        permission_body = {
            "type": "user",
            "role": role,
            "emailAddress": email_address
        }
        service.permissions().create(
            fileId=folder_id,
            body=permission_body,
            sendNotificationEmail=True,
            fields="id"
        ).execute()
        print(f"[+] Successfully shared folder with {email_address} (role: {role})")
    except Exception as e:
        print(f"[!] Warning: Sharing folder failed ({e}). Target may already own folder or restricted by domain policy.")


def sync_file(service, local_file: Path, parent_id: str) -> bool:
    """Upload or update file in Google Drive if missing or modified."""
    fname = local_file.name
    query = f"name = '{fname}' and '{parent_id}' in parents and trashed = false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name, size)").execute()
    files = results.get("files", [])

    # Idempotent skip if same file already exists
    if files:
        remote_size = int(files[0].get("size", -1))
        local_size = local_file.stat().st_size
        if remote_size == local_size:
            return False  # Skipped

    metadata = {"name": fname, "parents": [parent_id]}
    media = MediaFileUpload(str(local_file), resumable=True)
    service.files().create(body=metadata, media_body=media, fields="id").execute()
    return True


def mirror_directory(service, local_dir: Path, remote_parent_id: str, folder_cache: dict = None):
    """Recursively mirror local directory tree into Google Drive."""
    if folder_cache is None:
        folder_cache = {}

    for item in local_dir.iterdir():
        if item.name.startswith("."):
            continue

        if item.is_dir():
            cache_key = f"{remote_parent_id}/{item.name}"
            if cache_key not in folder_cache:
                subfolder_id = find_or_create_folder(service, item.name, remote_parent_id)
                folder_cache[cache_key] = subfolder_id
            else:
                subfolder_id = folder_cache[cache_key]

            mirror_directory(service, item, subfolder_id, folder_cache)
        elif item.is_file():
            uploaded = sync_file(service, item, remote_parent_id)
            status_txt = "[UPLOADED]" if uploaded else "[SYNCED]"
            print(f"  {status_txt} {item.relative_to(local_dir.parent)}")


def create_backup_zip(source_dir: Path, output_zip: Path) -> Path:
    """Create consolidated timestamped zip bundle."""
    print(f"[*] Packaging archive into {output_zip.name}...")
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.startswith("."):
                    continue
                file_path = Path(root) / file
                archive_name = file_path.relative_to(source_dir)
                zf.write(file_path, archive_name)
    print(f"[+] Archive created ({output_zip.stat().st_size / (1024*1024):.2f} MB)")
    return output_zip


def run_sync(
    vault_dir: Path,
    target_email: str = DEFAULT_TARGET_EMAIL,
    root_folder_name: str = DEFAULT_ROOT_FOLDER_NAME,
    as_zip: bool = False
):
    """Execute complete synchronization run."""
    if not vault_dir.exists():
        print(f"[!] Local vault directory '{vault_dir}' does not exist.")
        return

    print(f"\n[*] Initializing Google Drive Sync Pipeline...")
    service = get_drive_service()

    # 1. Ensure Root Folder on Google Drive
    root_id = find_or_create_folder(service, root_folder_name)
    print(f"[+] Target Google Drive Root: '{root_folder_name}' (ID: {root_id})")

    # 2. Grant permissions to Pushkar (phsnoida@gmail.com)
    if target_email:
        share_folder(service, root_id, target_email, role="writer")

    # 3. Synchronize Content
    if as_zip:
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        zip_path = vault_dir.parent / f"ReddiffBackup_{timestamp_str}.zip"
        create_backup_zip(vault_dir, zip_path)
        print(f"[*] Uploading zip archive to Google Drive...")
        sync_file(service, zip_path, root_id)
        print(f"[✓] Zip archive safely delivered to Google Drive.")
    else:
        print(f"[*] Mirroring directory tree to Google Drive...")
        mirror_directory(service, vault_dir, root_id)
        print(f"[✓] Directory tree synchronized with Google Drive.")


def main():
    parser = argparse.ArgumentParser(description="Google Drive Sync for Rediffmail Backup Suite")
    parser.add_argument("--vault", "-v", default="./backup_vault", help="Local backup vault directory (default: ./backup_vault)")
    parser.add_argument("--share", "-s", default=DEFAULT_TARGET_EMAIL, help=f"Google account email to grant access to (default: {DEFAULT_TARGET_EMAIL})")
    parser.add_argument("--folder", "-f", default=DEFAULT_ROOT_FOLDER_NAME, help=f"Root Google Drive folder name (default: {DEFAULT_ROOT_FOLDER_NAME})")
    parser.add_argument("--zip", action="store_true", help="Compress and upload backup vault as a single timestamped .zip archive")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--interval", type=int, default=3600, help="Daemon sync interval in seconds (default: 3600 / 1 hour)")

    args = parser.parse_args()
    vault_path = Path(args.vault).resolve()

    if args.daemon:
        print(f"[⚡] Google Drive Archival Daemon active. Interval: {args.interval}s")
        while True:
            try:
                run_sync(vault_path, target_email=args.share, root_folder_name=args.folder, as_zip=args.zip)
            except Exception as e:
                print(f"[!] Daemon error in sync cycle: {e}")
            print(f"[*] Sleeping for {args.interval} seconds... (Ctrl+C to stop)")
            time.sleep(args.interval)
    else:
        run_sync(vault_path, target_email=args.share, root_folder_name=args.folder, as_zip=args.zip)


if __name__ == "__main__":
    main()
