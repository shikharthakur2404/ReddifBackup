#!/usr/bin/env python3
"""
Rediffmail Pro Email & Attachment Archiver
==========================================
Protocol: IMAP over SSL (Port 993)
Features:
- Chronological partitioning: Year / Month / Day & Time Capsules
- Synchronized filesystem timestamps (mtime matches exact email date/time)
- Automatic MIME decoding and attachment isolation
- Incremental resume (skips already archived emails)
"""

import os
import sys
import re
import imaplib
import email
from email.header import decode_header
import email.utils
import argparse
import getpass
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_IMAP_SERVER = "imap.rediffmailpro.com"
DEFAULT_IMAP_PORT = 993


def clean_filename(s: str, max_len: int = 50) -> str:
    """Sanitize strings for safe filesystem naming across OS platforms."""
    if not s:
        return "unnamed"
    # Replace invalid chars with underscore
    s = re.sub(r'[\\/*?:"<>|\r\n\t]', "_", s).strip()
    # Collapse multiple spaces or underscores
    s = re.sub(r'[ _]+', '_', s)
    return s[:max_len].strip("._ ") or "unnamed"


def decode_mime_header(val: str) -> str:
    """Decode encoded MIME header values safely (UTF-8, Latin-1, Base64, QP)."""
    if not val:
        return ""
    decoded_fragments = []
    try:
        parts = decode_header(val)
        for fragment, encoding in parts:
            if isinstance(fragment, bytes):
                encoding = encoding or "utf-8"
                try:
                    decoded_fragments.append(fragment.decode(encoding, errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    decoded_fragments.append(fragment.decode("latin1", errors="replace"))
            else:
                decoded_fragments.append(str(fragment))
        return "".join(decoded_fragments).strip()
    except Exception:
        return str(val).strip()


def parse_email_datetime(hdr_date_str: str, internal_date_str: str = None) -> datetime:
    """
    Parse email timestamp with dual fallback:
    1. RFC-2822 Date header
    2. IMAP server INTERNALDATE
    3. Current UTC timestamp
    """
    if hdr_date_str:
        try:
            dt = email.utils.parsedate_to_datetime(hdr_date_str)
            if dt:
                return dt
        except Exception:
            pass

    if internal_date_str:
        try:
            # Format: "07-Nov-2026 07:52:14 +0000"
            clean_internal = internal_date_str.strip('"')
            return datetime.strptime(clean_internal.split()[0] + " " + clean_internal.split()[1], "%d-%b-%Y %H:%M:%S")
        except Exception:
            pass

    return datetime.now(timezone.utc)


def extract_internaldate(response_bytes: bytes) -> str:
    """Extract INTERNALDATE from IMAP response tuple."""
    if not response_bytes:
        return ""
    match = re.search(r'INTERNALDATE "([^"]+)"', response_bytes.decode(errors="ignore"))
    return match.group(1) if match else ""


def sync_file_mtime(file_path: Path, dt: datetime):
    """Update OS file modification timestamp to mirror email send/receive time."""
    try:
        ts = dt.timestamp()
        os.utime(file_path, (ts, ts))
    except Exception:
        pass


def save_attachment(part, target_dir: Path, email_dt: datetime) -> str:
    """Extract and save attachment part to target directory with synced mtime."""
    filename = part.get_filename()
    if not filename:
        return ""
    
    clean_name = clean_filename(decode_mime_header(filename), max_len=80)
    target_path = target_dir / clean_name
    
    # Avoid collision
    counter = 1
    stem = target_path.stem
    suffix = target_path.suffix
    while target_path.exists():
        target_path = target_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    payload = part.get_payload(decode=True)
    if payload:
        with open(target_path, "wb") as f:
            f.write(payload)
        sync_file_mtime(target_path, email_dt)
        return str(target_path.name)
    return ""


def process_folder(
    mail: imaplib.IMAP4_SSL,
    folder_name: str,
    base_output_dir: Path,
    organize_by: str = "capsule",
    save_eml: bool = True,
    extract_attachments: bool = True
):
    """
    Scan and archive emails from folder with Date & Time organization.
    
    organize_by modes:
    - 'capsule'    : folder / YYYY / MM-Mon / YYYY-MM-DD_HH-MM-AM_[Sender]_[Subject] / (eml + attachments)
    - 'date-split' : folder / YYYY / MM-Mon / (eml/ + attachments/)
    - 'flat'       : folder / (eml/ + attachments/) with date prefix
    """
    status, count_data = mail.select(f'"{folder_name}"', readonly=True)
    if status != "OK":
        print(f"[!] Access failed for folder: {folder_name}")
        return

    status, search_data = mail.search(None, "ALL")
    if status != "OK" or not search_data or not search_data[0]:
        print(f"[*] Folder '{folder_name}' has no messages.")
        return

    msg_ids = search_data[0].split()
    total = len(msg_ids)
    print(f"\n[+] Folder: '{folder_name}' | Messages: {total}")

    safe_folder = clean_filename(folder_name)

    for idx, msg_id in enumerate(msg_ids, start=1):
        mid_str = msg_id.decode()

        # Step 1: Fetch Headers and Server Internal Date
        status, header_data = mail.fetch(msg_id, "(INTERNALDATE BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
        subject = "No_Subject"
        sender = "Unknown"
        raw_date = ""
        internal_date = ""

        if status == "OK" and header_data:
            for item in header_data:
                if isinstance(item, tuple):
                    internal_date = extract_internaldate(item[0])
                    hdr_msg = email.message_from_bytes(item[1])
                    subject = clean_filename(decode_mime_header(hdr_msg.get("Subject", "")))
                    sender = clean_filename(decode_mime_header(hdr_msg.get("From", "")))
                    raw_date = hdr_msg.get("Date", "")

        # Step 2: Determine Date & Time
        email_dt = parse_email_datetime(raw_date, internal_date)
        year_str = email_dt.strftime("%Y")
        month_str = email_dt.strftime("%m-%b")
        date_folder_str = email_dt.strftime("%Y-%m-%d")
        time_folder_str = email_dt.strftime("%Y-%m-%d_%I-%M-%p")

        # Step 3: Determine Directory Paths based on organize_by
        if organize_by == "capsule":
            # Self-contained chronological container per message
            capsule_name = f"{time_folder_str}_{sender}_{subject}"[:90]
            capsule_dir = base_output_dir / safe_folder / year_str / month_str / capsule_name
            eml_path = capsule_dir / f"message_{mid_str}.eml"
            att_dir = capsule_dir / "attachments"
        elif organize_by == "date-split":
            # Partitioned by Year / Month with separate eml and attachment folders
            month_dir = base_output_dir / safe_folder / year_str / month_str
            eml_path = month_dir / "eml" / f"{time_folder_str}_{mid_str}_{subject}.eml"[:120]
            att_dir = month_dir / "attachments" / f"{time_folder_str}_{mid_str}_{subject}"[:80]
        else: # flat
            flat_dir = base_output_dir / safe_folder
            eml_path = flat_dir / "eml" / f"{time_folder_str}_{mid_str}_{subject}.eml"[:120]
            att_dir = flat_dir / "attachments" / f"{time_folder_str}_{mid_str}_{subject}"[:80]

        # Resume check: Skip if already fetched
        if save_eml and eml_path.exists():
            print(f"  [{idx}/{total}] [SKIP] {time_folder_str} | ID:{mid_str} (Already archived)")
            continue

        # Step 4: Fetch Full RFC-822 Payload
        status, full_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK" or not full_data or not isinstance(full_data[0], tuple):
            print(f"  [{idx}/{total}] [FAIL] ID:{mid_str} fetch error.")
            continue

        raw_bytes = full_data[0][1]

        # Step 5: Save .EML with synced timestamp
        if save_eml:
            eml_path.parent.mkdir(parents=True, exist_ok=True)
            with open(eml_path, "wb") as f:
                f.write(raw_bytes)
            sync_file_mtime(eml_path, email_dt)

        # Step 6: Extract Attachments with synced timestamps
        saved_files = []
        if extract_attachments:
            msg_obj = email.message_from_bytes(raw_bytes)
            if msg_obj.is_multipart():
                for part in msg_obj.walk():
                    disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in disposition.lower() or part.get_filename():
                        att_dir.mkdir(parents=True, exist_ok=True)
                        f_name = save_attachment(part, att_dir, email_dt)
                        if f_name:
                            saved_files.append(f_name)

        att_summary = f" | Attachments [{len(saved_files)}]: {', '.join(saved_files[:2])}" if saved_files else ""
        print(f"  [{idx}/{total}] [OK] {time_folder_str} | {subject}{att_summary}")


def main():
    parser = argparse.ArgumentParser(description="Rediffmail Pro Email & Attachment Archiver (Date & Time Partitioned)")
    parser.add_argument("--user", "-u", help="Rediffmail Pro full email address (e.g. name@domain.com)")
    parser.add_argument("--password", "-p", help="Email password (prompted if omitted)")
    parser.add_argument("--server", "-s", default=DEFAULT_IMAP_SERVER, help=f"IMAP host (default: {DEFAULT_IMAP_SERVER})")
    parser.add_argument("--port", "-P", type=int, default=DEFAULT_IMAP_PORT, help=f"IMAP port (default: {DEFAULT_IMAP_PORT})")
    parser.add_argument("--output", "-o", default="./backup_vault", help="Target output directory")
    parser.add_argument("--folder", "-f", default=None, help="Target specific folder (e.g. 'INBOX'). If omitted, backs up all folders.")
    parser.add_argument(
        "--organize-by",
        choices=["capsule", "date-split", "flat"],
        default="capsule",
        help="Date/Time Organization style: 'capsule' (Year/Month/Time-Capsule folder with eml+attachments, default), 'date-split' (Year/Month with separate eml & attachments folders), or 'flat'."
    )
    parser.add_argument("--no-eml", action="store_true", help="Skip saving raw .eml files")
    parser.add_argument("--no-attachments", action="store_true", help="Skip extracting attachment files")

    args = parser.parse_args()

    user = args.user or input("Rediffmail Pro Email: ").strip()
    if not user:
        print("[!] Email is required.")
        sys.exit(1)

    password = args.password or getpass.getpass("Password: ")
    if not password:
        print("[!] Password is required.")
        sys.exit(1)

    base_out = Path(args.output).resolve()
    base_out.mkdir(parents=True, exist_ok=True)

    print(f"\n[*] Connecting to {args.server}:{args.port} (SSL)...")
    try:
        mail = imaplib.IMAP4_SSL(args.server, args.port)
        mail.login(user, password)
        print(f"[+] Authentication successful: {user}")
    except Exception as e:
        print(f"[!] IMAP Connection/Auth Failed: {e}")
        print("\nNote: If IMAP is disabled by your administrator, use Option 2 (Browser Extension HUD).")
        sys.exit(1)

    try:
        if args.folder:
            folders = [args.folder]
        else:
            status, folder_list = mail.list()
            folders = []
            if status == "OK":
                for f_entry in folder_list:
                    match = re.search(r'"([^"]+)"$', f_entry.decode())
                    if match:
                        folders.append(match.group(1))
                    else:
                        parts = f_entry.decode().split()
                        folders.append(parts[-1].strip('"'))
            else:
                folders = ["INBOX"]

        print(f"[*] Scanning Folders: {folders}")
        print(f"[*] Chronological Layout: '{args.organize_by}'")

        for folder in folders:
            process_folder(
                mail=mail,
                folder_name=folder,
                base_output_dir=base_out,
                organize_by=args.organize_by,
                save_eml=not args.no_eml,
                extract_attachments=not args.no_attachments
            )

        print(f"\n[✓] Backup Complete. Chronological archive stored at:\n    {base_out}")

    finally:
        try:
            mail.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
