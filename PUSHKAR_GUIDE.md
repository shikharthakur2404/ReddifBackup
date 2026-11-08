# Pushkar's Rediffmail Backup Guide

The current destination is the local `backup_vault/` folder. Historical mail is
being archived through Brave because IMAP and POP3 exposed only recent messages.
The archive is not complete: see [ARCHIVE_STATUS.md](ARCHIVE_STATUS.md).

**Automation setup is pending macOS permission:** the installed job cannot yet
read this Downloads workspace. See the permission section below.

## Resume the historical archive

Use the existing workspace to retain the downloaded files and resume manifest:

```bash
cd /Users/shikharthakur/Downloads/ReddifBackup
```

A fresh Git clone contains code and documentation only. Mailbox data, attachments,
credentials, and the resume manifest are excluded from Git.

1. After the server quota resets, open Brave with its local debugging port.
   If Brave is already running without that port, quit it normally first.

   ```bash
   open -a 'Brave Browser' --args --remote-debugging-address=127.0.0.1 --remote-debugging-port=9223 'https://webmail.rediffmailpro.com/'
   ```

2. Sign in to Rediffmail in Brave and leave the mailbox tab open. No password
   needs to be added to a script or configuration file.

3. With Node.js 22+ and Python 3 installed, run:

   ```bash
   node webmail_archive.mjs
   python3 extract_webmail.py
   python3 vault_inventory.py
   ```

The downloader re-enumerates the folders, verifies saved originals against their
SHA-256 hashes, and skips intact files. The extractor uses stable attachment paths,
so rerunning it does not create another copy of each attachment.

Run extraction and inventory even if the download stops at the daily quota. The
extractor returns exit code 1 when messages are still missing; inspect its report
rather than treating that exit code alone as evidence of corrupt files.

## Files and verification

```text
backup_vault/
├── Webmail/
│   ├── Inbox/2026-10/<message-id>/
│   │   ├── message.eml
│   │   └── attachments/
│   ├── manifest.json
│   └── verification.json
├── inventory.json
└── ... earlier IMAP/POP3 backups
```

- `message.eml` contains the original email and its embedded attachments.
- `manifest.json` records enumerated messages, saved paths, sizes, and hashes.
- `verification.json` records extracted attachment hashes and errors. Only
  `verified: true` confirms that the enumerated webmail archive passed verification.
- `inventory.json` lists actual local files and hashes. It does not independently
  certify historical completeness.

Webmail folders use UTC months; file modification times use the server message
timestamp. The earlier IMAP/POP3 files remain in place. Counts across the whole
vault include overlap between those backups and Webmail.

## Daily quota and session expiry

On November 8, Rediffmail returned: “You have exhausted the number of limit for
the day.” It subsequently returned `INVALID_SESSION`.

Try again on November 9. The response supplied no reset time, timezone, quota
size, or rolling-window rule. If the quota remains exhausted, wait longer or ask
the mail administrator for the actual limit. Signing in again restores a session;
it is not known to reset the daily quota. A daily local job is installed for 14:00 Mac time, with downloads first eligible on November 9. It still requires a valid browser session.

The downloader rejects HTML error pages instead of saving them as email files.
It stops on a recognized daily-quota response and preserves completed downloads.
Leave Brave open and signed in for the daily job. Close it when archival is complete to close its debugging port.

## Checks

```bash
python3 -m unittest -q test_scheduled_backup.py test_webmail_archive.py test_rediff_backup.py
node --check browser_cdp.mjs
node --check webmail_archive.mjs
```

Ten Python tests passed on November 8. These cover the existing archive helpers
and attachment extraction, including binary data, duplicate filenames, safe paths,
repeat runs, corrupt originals, same-day retry suppression, and notification when the browser is unavailable. They do not prove that the server will serve
all remaining messages after its quota resets.

## Other methods

### GitHub and mobile access

Push code, tests, and these Markdown guides to GitHub. Keep mailbox originals,
attachments, credentials, session tokens, and private logs local and Git-ignored.
You can read the repository and handoff note on a phone, but this pipeline runs
on the Mac: it depends on desktop Brave's localhost debugging port and macOS
LaunchAgents. GitHub Actions cannot access that local browser session. A phone
does not replace the Mac for this implementation.

The original IMAP script remains available for recent mail:

```bash
python3 rediff_backup.py --user your_email@domain.com
```

Google Drive is optional and was not used for this run. It requires separately
configured credentials before `gdrive_sync.py` can upload anything. The extension
and console crawler are older alternatives; their download counters do not verify
a complete historical archive. Use the Brave pipeline and verification report.

## Daily schedule

The installed LaunchAgent is `com.reddifbackup.daily`, scheduled for 14:00 local
Mac time. Today’s known exhausted quota is skipped; the first eligible download
run is November 9. No chat session or coding assistant needs to stay open.

Keep the Mac powered on, your macOS user logged in, and Brave running with the
local debugging port and an authenticated Rediffmail tab. A sleeping or powered-off
Mac may delay or miss the intended time. The job does not wake or power on the Mac.
Expired sessions need a manual sign-in; the runner requests one through a macOS
notification. Notification delivery depends on your macOS notification settings.

If about 46 additional originals can be saved per day, 221 remaining originals
would need about five more successful daily runs. This is an estimate, not a
verified quota. Further expiry, quota changes, or new messages can extend it.

Private run logs are saved in `logs/archive-*.log`. Scheduler output is in
`logs/scheduler.log` and `logs/scheduler-error.log`. Inspect the job with:

```bash
launchctl print gui/$(id -u)/com.reddifbackup.daily
```

To disable the daily job:

```bash
launchctl bootout gui/$(id -u)/com.reddifbackup.daily
```

To install it again, run `python3 install_schedule.py --install`. Once the
historical archive is verified complete, future scheduled invocations do no more
downloading. This is a finite historical archive job, not ongoing new-mail sync.

## macOS permission required before automation works

The LaunchAgent is installed, but its smoke test failed with `Operation not
permitted` when Python tried to read `scheduled_backup.py` inside Downloads.
**Unattended execution is blocked until macOS grants the scheduled interpreter
access.** The intended schedule is 14:00 local time; November 9 is the first
eligible download date, provided this permission is resolved.

In System Settings → Privacy & Security, grant Python Downloads access under
Files and Folders if available. Otherwise add the scheduled interpreter,
`/Library/Developer/CommandLineTools/usr/bin/python3`, under Full Disk Access.
That broader permission applies to this interpreter, not just the backup script.
After enabling access, smoke-test the job and inspect its logs:

```bash
launchctl kickstart gui/$(id -u)/com.reddifbackup.daily
cat logs/scheduler.log
cat logs/scheduler-error.log
```

On November 8 the expected successful smoke-test output is “Already attempted
today; waiting for the next daily run.” Existing error log lines may remain from
the earlier failed attempt; inspect the newest output. If macOS still blocks it,
the schedule cannot perform a backup until that access issue is resolved.
