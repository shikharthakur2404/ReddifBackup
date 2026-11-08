# Rediffmail Pro Backup Suite

### Historical webmail archive through Brave

This route uses the signed-in Rediffmail tab through a localhost CDP connection.
It enumerates every server folder, follows the observed `maillist` pagination
cursor to its end, and downloads original RFC-822 messages through `downloadmail`.
The browser pipeline does not persist passwords or session cookies to project files. Opening messages in the UI is
unnecessary. Keep Brave open during the run.

When Brave is closed, start it from Terminal:

```bash
open -a 'Brave Browser' --args --remote-debugging-address=127.0.0.1 --remote-debugging-port=9223 'https://webmail.rediffmailpro.com/'
```

Sign in, then run with Node.js 22+ and Python 3:

```bash
node webmail_archive.mjs && python3 extract_webmail.py && python3 vault_inventory.py
```

Originals and extracted attachments go into `backup_vault/Webmail/`, organized
by folder, UTC month, and stable message ID. `manifest.json` records enumeration
and original-file SHA-256 checksums; `verification.json` records attachment
checksums and any failures. Completion requires `verified: true` in the latter.
Rerunning verifies existing originals before skipping them and rewrites extracted
attachments at stable paths. The earlier IMAP/POP archive remains in place;
there can be duplicates across those older backups and the Webmail archive.
Keep Brave open and signed in for scheduled runs. Close it after archival is complete to close the debugging port.

The server can impose a daily download quota. The archiver stops on that response
instead of saving the HTML error as an email. After the quota resets, sign in
again if necessary and rerun the same command to resume from verified files.

### Status as of November 8, 2026

The historical archive is **incomplete**. See [ARCHIVE_STATUS.md](ARCHIVE_STATUS.md)
for the verified counts and next steps, and [PUSHKAR_GUIDE.md](PUSHKAR_GUIDE.md)
for the restart procedure.

- Enumerated 267 messages across Inbox, Sent, and Trash, dated April 7–November 7.
- Saved 46 webmail originals and extracted 47 attachments; 221 originals remain.
- The server reported its daily download limit, then `INVALID_SESSION`.
- Retry on November 9; the server did not disclose its reset time or timezone.
  Midnight and a rolling 24-hour window are possibilities, not confirmed rules.
- Local storage is the selected destination. No Google Drive upload completed.

If a download run stops early, extract and inventory the saved portion separately:

```bash
python3 extract_webmail.py
python3 vault_inventory.py
```

The extractor returns exit code 1 while the archive is incomplete, even if every
saved original and extracted attachment passes its checksum checks. This is expected.
The general inventory records file hashes; use `Webmail/verification.json` to assess
webmail completeness. A daily macOS job is installed for 14:00 local time; its first download attempt is November 9. See the guide for session requirements and logs.

### Other archive methods

---

### Option 1: Terminal IMAP Archiver (`rediff_backup.py`)
Requires Python 3 (standard library only). Direct IMAP protocol pipeline with date/time partitioning and OS timestamp synchronization. In this mailbox, IMAP/POP3 exposed only recent messages; use the Brave route for historical mail.

1. **Run full backup with chronological capsules:**
   ```bash
   python3 rediff_backup.py --user your_name@domain.com
   ```
2. **Date/Time Organization Layouts (`--organize-by`):**
   - **`capsule` (Default):** Dedicated chronological folder per email containing its `.eml` and its attachments:
     ```text
     backup_vault/
     └── INBOX/
         └── 2026/
             └── 11-Nov/
                 └── 2026-11-07_07-52-AM_Rajesh_K2_TA_of_October_month/
                     ├── message_104.eml
                     └── attachments/
                         └── TA_October.xlsx
     ```
   - **`date-split`:** Grouped by Year and Month, segregating raw emails and attachments:
     ```text
     backup_vault/INBOX/2026/11-Nov/eml/
     backup_vault/INBOX/2026/11-Nov/attachments/
     ```
   - **`flat`:** Single folder per mailbox with ISO timestamp prefixes (`YYYY-MM-DD_HH-MM-AM_...`).

3. **OS Timestamp Synchronization (`mtime`):**
   Every exported `.eml` file and extracted attachment file has its filesystem modification timestamp (`mtime`) set to match the exact email send/receive date & time. Sorting by Date Modified in Finder or terminal reflects the true historical timeline.

4. **Additional Flags:**
   - `--folder INBOX` : Restrict sync to specific mailbox folder.
   - `--no-eml` : Extract only attachment files (skip `.eml` messages).
   - `--output ./my_backup` : Custom output directory (default: `./backup_vault`).
   - `--upload-gdrive` : Auto-upload and mirror backup vault to Google Drive.
   - `--share-gdrive phsnoida@gmail.com` : Auto-grant permissions to Pushkar (default: `phsnoida@gmail.com`).
   - `--gdrive-zip` : Package as a consolidated `.zip` archive before uploading.

---

### Option 2: Google Drive Automated Pipeline (`gdrive_sync.py`)
Optional cloud synchronizer. Requires Google client libraries and local OAuth credentials (`credentials.json` and a generated `token.json`), or service-account credentials. It is not configured for the current local-only archive.

1. **Direct Synchronize:**
   ```bash
   python3 gdrive_sync.py --share phsnoida@gmail.com
   ```
2. **Background Automation Daemon (Syncs every hour):**
   ```bash
   python3 gdrive_sync.py --daemon --interval 3600
   ```

---

### Option 3: Edge / Chrome Extension HUD (Webmail Active Session)
Use when IMAP/POP is restricted by corporate administrator or 2FA policies.

1. In Edge/Chrome, go to:
   - `edge://extensions` or `chrome://extensions`
2. Enable **Developer mode** toggle.
3. Click **Load unpacked** and select:
   `/Users/shikharthakur/Downloads/ReddifBackup/extension`
4. Refresh your active Rediffmail Pro webmail tab.
5. Click **Scan Mail List** -> **Download Attachments in View**.

### Daily local automation

**Setup blocker:** launchd currently cannot read the workspace in Downloads.
The job is installed but will not execute successfully until Python receives
macOS permission. See the permission section in [PUSHKAR_GUIDE.md](PUSHKAR_GUIDE.md).

```bash
python3 install_schedule.py --install
```

This installs `com.reddifbackup.daily` as a per-user macOS LaunchAgent at 14:00
local time. Installation suppresses downloads on the installation day. Keep the
Mac available and Brave open with its debugging port and a signed-in mailbox tab.
The runner never stores a password or signs in automatically. It notifies you
when login is required, avoids multiple download attempts on the same calendar
day, extracts partial downloads, and skips future downloads once verification
reports completion. Private logs are under the Git-ignored `logs/` directory.

For another coding assistant, use [ANTIGRAVITY_HANDOFF.md](ANTIGRAVITY_HANDOFF.md).
