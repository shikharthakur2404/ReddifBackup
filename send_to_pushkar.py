#!/usr/bin/env python3
import subprocess

recipient = "phsnoida@gmail.com"
subject = "Rediffmail Pro Complete Backup Suite & Operational Guide"

body = """Hey Pushkar,

Here is the complete operational guide, repository access, and tools to back up all Rediffmail Pro emails and attachments into organized chronological capsules.

============================================================
1. GITHUB REPOSITORY
============================================================
Repo: https://github.com/shikharthakur2404/ReddifBackup
All code, tests, documentation, and extension HUD files are stored here.

============================================================
2. QUICK TERMINAL BACKUP (Terminal Route)
============================================================
Run this directly in your terminal to back up all emails and attachments into date/time capsules:

    git clone https://github.com/shikharthakur2404/ReddifBackup.git
    cd ReddifBackup
    python3 rediff_backup.py --user pushkar.sharma@mediassist.in

All downloaded files are organized under ./backup_vault/ by:
Year -> Month -> Date-Time-Capsule -> (message.eml + attachments/)
(The filesystem timestamps are automatically synced to match the original email date/time).

============================================================
3. GOOGLE DRIVE AUTOMATION (phsnoida@gmail.com)
============================================================
To auto-upload the entire vault to Google Drive and share it directly with phsnoida@gmail.com:

    python3 rediff_backup.py --user pushkar.sharma@mediassist.in --upload-gdrive

Or run the continuous hourly backup daemon:

    python3 gdrive_sync.py --share phsnoida@gmail.com --daemon --interval 3600

============================================================
4. HISTORICAL DEEP CRAWLER (April - November 2026)
============================================================
If your webmail has older emails (April - October) that the corporate IMAP server doesn't expose:

1. Open Rediffmail Pro in Microsoft Edge (logged in).
2. Scroll to the top of your Inbox.
3. Press Cmd + Option + J (opens Console).
4. Paste the self-contained crawler from backup_console.js in the repo and press Enter.

It will automatically scroll through your entire mailbox history down to April 2026 and download all attachments directly to your ~/Downloads folder.

Best regards,
Shikhar
"""

escaped_body = body.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

script = """
tell application "Mail"
    set theSubject to "{}"
    set theBody to "{}"
    set theMsg to make new outgoing message with properties {{subject:theSubject, content:theBody, visible:true}}
    tell theMsg
        make new to recipient at end of to recipients with properties {{address:"{}", name:"Pushkar"}}
    end tell
    activate
end tell
""".format(subject, escaped_body, recipient)

subprocess.run(["osascript", "-e", script])
print("[+] Email drafted in Apple Mail ready to send to phsnoida@gmail.com")
