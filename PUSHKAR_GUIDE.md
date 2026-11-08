# Pushkar's Quick-Start & Operational Guide 🚀
### Rediffmail Pro Email & Attachment Archiver Suite

Hey Pushkar! This repository contains the complete automated toolchain to back up all Rediffmail Pro emails and their attachments into clean, chronological date/time folders.

Everything has been built, tested, and verified. Follow this exact guide to run your backup.

---

## ⚡ Step 1: Clone & Verify Setup

Open your Terminal (macOS/Linux) or Command Prompt/PowerShell (Windows):

```bash
git clone https://github.com/shikharthakur2404/ReddifBackup.git
cd ReddifBackup
```

Run the built-in test suite to ensure your Python environment is ready:
```bash
python3 test_rediff_backup.py -v
```
*(You should see `Ran 5 tests ... OK`)*

---

## 🚀 Step 2: Run the Terminal Archiver (Recommended)

Run the script with your company Rediffmail Pro email address:

```bash
python3 rediff_backup.py --user your_email@domain.com
```

- You will be prompted to enter your password securely (keystrokes will be hidden).
- The script connects over SSL (Port 993) to Rediffmail.
- It will automatically scan all mail folders (INBOX, Sent, etc.).
- It downloads the full `.eml` email and extracts every single attachment.

### Where Do The Files Go?
All files are saved inside `./backup_vault/` organized neatly by **Year $\rightarrow$ Month $\rightarrow$ Exact Date & Time Capsule**:

```text
backup_vault/
└── INBOX/
    └── 2026/
        └── 11-Nov/
            └── 2026-11-07_07-52-AM_Rajesh_K2_TA_of_October_month/
                ├── message_104.eml        <-- Full raw email
                └── attachments/           <-- Extracted attachments
                    ├── TA_October.xlsx
                    └── receipt.pdf
```

> **Pro Tip:** The script automatically synchronizes the filesystem's `Date Modified` timestamp. When you open Finder or File Explorer and sort by **Date Modified**, all emails and attachments will be ordered in true chronological order.

---

## 🛠️ Step 3: Useful Options & Flags

| Flag | What it does | Example |
| :--- | :--- | :--- |
| `--folder` | Sync only a specific folder | `python3 rediff_backup.py --user your@domain.com --folder INBOX` |
| `--no-eml` | Download **only** attachments (skips `.eml` mail files) | `python3 rediff_backup.py --user your@domain.com --no-eml` |
| `--organize-by date-split` | Put all EMLs in `eml/` and attachments in `attachments/` by month | `python3 rediff_backup.py --user your@domain.com --organize-by date-split` |
| `--output <dir>` | Change destination folder | `python3 rediff_backup.py --user your@domain.com --output ~/Desktop/MyRediffBackup` |

> **Safe to Interrupt & Resume:** If you stop the script (`Ctrl+C`), you can safely re-run it anytime. It automatically checks which emails have already been archived and skips them without re-downloading.

---

## 🌐 Fallback Option: Browser Extension HUD

If your company domain administrator has blocked external IMAP access (port 993):

1. Open **Microsoft Edge** or **Google Chrome** where your Rediffmail Pro webmail is currently logged in.
2. Open a new tab and go to `edge://extensions` (or `chrome://extensions`).
3. Turn on the **Developer mode** toggle (top right / left).
4. Click **Load unpacked** and select the `extension/` folder inside this repository:
   ```text
   ReddifBackup/extension
   ```
5. Switch back to your open Rediffmail Pro tab and hit **Refresh**.
6. You will see a dark **`⚡ REDIFF ARCHIVER HUD`** panel docked at the bottom right.
7. Click **Scan Mail List** $\rightarrow$ **Download Attachments in View**. All attachments will download directly to your browser's `Downloads/ReddiffBackup/` folder.

---

## ❓ Need Help / Troubleshooting

- **"Authentication Failed"**: Verify your password. If your domain uses a custom mail shard instead of `imap.rediffmailpro.com`, add `--server mail.yourdomain.com`.
- **"Connection Timeout"**: Make sure you are not on a restricted VPN or firewall that blocks port 993, or use the Browser Extension HUD.
