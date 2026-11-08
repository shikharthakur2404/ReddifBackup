# Rediffmail Pro Backup Suite

Two deployment vectors to archive emails and extract attachments:

---

### Option 1: Terminal IMAP Archiver (`rediff_backup.py`)
Requires Python 3 (standard library only). Direct IMAP protocol pipeline with date/time partitioning and OS timestamp synchronization.

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

---

### Option 2: Edge / Chrome Extension HUD (Webmail Active Session)
Use when IMAP/POP is restricted by corporate administrator or 2FA policies.

1. In Edge/Chrome, go to:
   - `edge://extensions` or `chrome://extensions`
2. Enable **Developer mode** toggle.
3. Click **Load unpacked** and select:
   `/Users/shikharthakur/Downloads/ReddifBackup/extension`
4. Refresh your active Rediffmail Pro webmail tab.
5. Click **Scan Mail List** -> **Download Attachments in View**.
