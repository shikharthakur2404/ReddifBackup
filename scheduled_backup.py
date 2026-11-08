#!/usr/bin/env python3
"""Daily local archive runner. Requires a signed-in Brave tab; never stores a password."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def notify(message):
    subprocess.run(['osascript', '-e', 'display notification ' + json.dumps(message)
                    + ' with title "Rediffmail backup"'], check=False)


def main():
    os.chdir(ROOT)
    with (ROOT / '.archive-run.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        return run_backup()


def run_backup():
    report_path = ROOT / 'backup_vault/Webmail/verification.json'
    manifest_path = ROOT / 'backup_vault/Webmail/manifest.json'
    if report_path.exists() and manifest_path.exists():
        report = json.loads(report_path.read_text())
        if report.get('verified') and report_path.stat().st_mtime >= manifest_path.stat().st_mtime:
            print('Historical archive already verified; no download needed.', flush=True)
            return 0
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    state_path = logs / 'schedule_state.json'
    today = datetime.now().strftime('%Y-%m-%d')
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state.get('last_attempt_date') == today:
        print('Already attempted today; waiting for the next daily run.', flush=True)
        return 0
    log_path = logs / ('archive-' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.log')
    node = shutil.which('node')
    if not node:
        notify('Node.js was not found. Check the backup runner PATH.')
        return 1
    # Use the running browser; do not relaunch, close, or change the user's tabs.
    try:
        with urlopen('http://127.0.0.1:9223/json/list', timeout=5) as response:
            tabs = json.load(response)
        ready = any(t.get('type') == 'page' and t.get('url', '').startswith(
            'https://webmail.rediffmailpro.com/ajaxprism/') for t in tabs)
        if not ready:
            raise RuntimeError('No mailbox tab')
    except Exception:
        notify('Open Brave with the backup debugging port and sign in to Rediffmail. See PUSHKAR_GUIDE.md.')
        log_path.write_text('Browser unavailable or no mailbox tab. No downloads attempted.\n')
        return 1
    with log_path.open('w') as log:
        state_path.write_text(json.dumps({'last_attempt_date': today}) + '\n')
        log.write('Run started ' + datetime.now().isoformat() + '\n')
        log.flush()
        try:
            result = subprocess.run([node, str(ROOT / 'webmail_archive.mjs')],
                                    stdout=log, stderr=subprocess.STDOUT, timeout=7200)
            download_code = result.returncode
        except subprocess.TimeoutExpired:
            log.write('Downloader exceeded two hours and was stopped.\n')
            download_code = 1
        # Extract and report saved files even when the server stops the download.
        for script in ('extract_webmail.py', 'vault_inventory.py'):
            subprocess.run([sys.executable, str(ROOT / script)], stdout=log,
                           stderr=subprocess.STDOUT, timeout=1800)
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    if report.get('verified') and download_code == 0:
        notify('Historical archive complete and verified. Files are in backup_vault/Webmail.')
        return 0
    text = log_path.read_text()
    if 'INVALID_SESSION' in text:
        notify('Rediffmail session expired. Sign in again in Brave; the next daily run will resume.')
    elif 'DAILY_DOWNLOAD_LIMIT' in text:
        notify('Daily download limit reached. Saved files verified; next daily run will resume.')
    else:
        notify('Backup is incomplete. Check the latest archive log in ReddifBackup/logs.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
