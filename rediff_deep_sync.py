#!/usr/bin/env python3
"""
Rediffmail Pro Deep Historical Terminal Extractor
=================================================
Probes:
1. IMAP Full History (unrestricted INBOX search, subfolder recursive crawl)
2. POP3 Historical Fetch (pop.rediffmailpro.com:995)
Downloads all emails and attachments into ./backup_vault
"""

import os
import sys
import re
import imaplib
import poplib
import email
from email.header import decode_header
import email.utils
import argparse
import getpass
from pathlib import Path
from datetime import datetime, timezone

# Import core helpers from rediff_backup
from rediff_backup import (
    clean_filename,
    decode_mime_header,
    parse_email_datetime,
    sync_file_mtime,
    save_attachment,
    process_folder,
    DEFAULT_IMAP_SERVER,
    DEFAULT_IMAP_PORT,
)

DEFAULT_POP_SERVER = "pop.rediffmailpro.com"
DEFAULT_POP_PORT = 995


def probe_pop3_messages(user: str, password: str, base_out: Path, save_eml: bool = True, extract_attachments: bool = True):
    """Attempt historical download via POP3 over SSL."""
    print(f"\n[*] Probing POP3 Server ({DEFAULT_POP_SERVER}:{DEFAULT_POP_PORT})...")
    try:
        pop_client = poplib.POP3_SSL(DEFAULT_POP_SERVER, DEFAULT_POP_PORT)
        pop_client.user(user)
        pop_client.pass_(password)
        num_messages, total_bytes = pop_client.stat()
        print(f"[+] POP3 Authentication Successful!")
        print(f"[+] POP3 Mailbox Status: {num_messages} total messages ({total_bytes / (1024*1024):.2f} MB)")

        if num_messages <= 0:
            print("[*] POP3 reported 0 messages.")
            pop_client.quit()
            return 0

        target_dir = base_out / "POP3_Inbox"
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"[*] Starting POP3 Full Historical Download ({num_messages} messages)...")
        for i in range(1, num_messages + 1):
            try:
                raw_lines = pop_client.retr(i)[1]
                raw_bytes = b"\r\n".join(raw_lines)
                msg_obj = email.message_from_bytes(raw_bytes)

                subject = clean_filename(decode_mime_header(msg_obj.get("Subject", "")))
                sender = clean_filename(decode_mime_header(msg_obj.get("From", "")))
                raw_date = msg_obj.get("Date", "")
                email_dt = parse_email_datetime(raw_date)

                year_str = email_dt.strftime("%Y")
                month_str = email_dt.strftime("%m-%b")
                time_folder_str = email_dt.strftime("%Y-%m-%d_%I-%M-%p")

                capsule_name = f"{time_folder_str}_{sender}_{subject}"[:90]
                capsule_dir = target_dir / year_str / month_str / capsule_name
                eml_path = capsule_dir / f"message_pop_{i}.eml"
                att_dir = capsule_dir / "attachments"

                if eml_path.exists():
                    print(f"  [{i}/{num_messages}] [SKIP] {time_folder_str} | {subject} (already exists)")
                    continue

                capsule_dir.mkdir(parents=True, exist_ok=True)
                if save_eml:
                    with open(eml_path, "wb") as f:
                        f.write(raw_bytes)
                    sync_file_mtime(eml_path, email_dt)

                saved_files = []
                if extract_attachments and msg_obj.is_multipart():
                    for part in msg_obj.walk():
                        disp = str(part.get("Content-Disposition", ""))
                        if "attachment" in disp.lower() or part.get_filename():
                            att_dir.mkdir(parents=True, exist_ok=True)
                            fname = save_attachment(part, att_dir, email_dt)
                            if fname:
                                saved_files.append(fname)

                att_txt = f" | Attachments [{len(saved_files)}]: {', '.join(saved_files[:2])}" if saved_files else ""
                print(f"  [{i}/{num_messages}] [OK] {time_folder_str} | {subject}{att_txt}")

            except Exception as ex:
                print(f"  [{i}/{num_messages}] [ERROR] Message {i}: {ex}")

        pop_client.quit()
        return num_messages
    except Exception as e:
        print(f"[!] POP3 Probe Failed or Restricted: {e}")
        return -1


def probe_imap_deep(user: str, password: str, base_out: Path, save_eml: bool = True, extract_attachments: bool = True):
    """Probe IMAP using unrestricted pattern search and explicit INBOX."""
    print(f"\n[*] Probing IMAP Server ({DEFAULT_IMAP_SERVER}:{DEFAULT_IMAP_PORT})...")
    try:
        mail = imaplib.IMAP4_SSL(DEFAULT_IMAP_SERVER, DEFAULT_IMAP_PORT)
        mail.login(user, password)
        print(f"[+] IMAP Authentication Successful: {user}")

        # List ALL folders recursively
        status, folder_list = mail.list(directory='""', pattern='*')
        folders = []
        if status == "OK":
            for f in folder_list:
                match = re.search(r'"([^"]+)"$', f.decode())
                if match:
                    folders.append(match.group(1))
                else:
                    parts = f.decode().split()
                    folders.append(parts[-1].strip('"'))

        print(f"[*] Detected IMAP Folders (Recursive): {folders}")

        for folder in folders:
            # Query folder
            process_folder(
                mail=mail,
                folder_name=folder,
                base_output_dir=base_out,
                organize_by="capsule",
                save_eml=save_eml,
                extract_attachments=extract_attachments
            )

        mail.logout()
    except Exception as e:
        print(f"[!] IMAP Deep Probe Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Rediffmail Pro Deep Historical Terminal Extractor")
    parser.add_argument("--user", "-u", default="pushkar.sharma@mediassist.in", help="Email address")
    parser.add_argument("--password", "-p", help="Password")
    parser.add_argument("--output", "-o", default="./backup_vault", help="Target output directory")

    args = parser.parse_args()
    user = args.user or input("Email: ").strip()
    password = args.password or getpass.getpass(f"Password for {user}: ")

    base_out = Path(args.output).resolve()
    base_out.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print("⚡ REDIFFMAIL PRO DEEP TERMINAL SYNC")
    print("="*60)

    # Vector 1: Test POP3 Historical Dump
    # Many mail servers restrict IMAP to 15-30 days, while POP3 has the full history
    pop_count = probe_pop3_messages(user, password, base_out)

    # Vector 2: Run Recursive IMAP Deep Probe
    probe_imap_deep(user, password, base_out)

    print(f"\n[✓] Terminal Operation Finished. Inspect: {base_out}")


if __name__ == "__main__":
    main()
