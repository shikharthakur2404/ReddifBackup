# Archive status — November 8, 2026

**Incomplete; resumable. Destination: local disk.**

## Verified progress

| Scope | Messages | Extracted attachments | Coverage |
| --- | ---: | ---: | --- |
| Earlier IMAP/POP3 vault | 60 | 57 | October 27–November 7, 2026 |
| New Webmail archive | 46 | 47 | October 6–November 7, 2026 |
| Combined files on disk | 106 | 104 | Includes overlap between methods |

The 47 Webmail attachments total 84,285,006 bytes. Seven attachments from messages
before October 27 extend the earlier IMAP coverage. Saved originals passed SHA-256
verification; extraction reported no attachment errors. The completion report
still records 221 missing originals and `verified: false`.

## Mailbox enumeration

| Folder | Enumerated messages |
| --- | ---: |
| Inbox | 206 |
| Sent | 56 |
| Trash | 5 |
| Junk | 0 |
| Drafts | 0 |
| Total | 267 |

Enumeration followed the webmail API pagination to its end for each folder.
The listed messages span April 7–November 7, 2026, with messages in every month.
Enumeration proves that message entries are visible; it does not prove that all
message bodies and attachments have been downloaded.

## Current blocker and next run

The original-message endpoint returned an HTML page stating its daily download
limit was exhausted. A subsequent API request returned `INVALID_SESSION`.
The normal individual-attachment route could not be verified after session expiry.

Retry on November 9 after signing into Brave. The actual quota reset time and
policy are unknown; a next-day retry is a suggested check, not a guaranteed reset.
A per-user macOS job, `com.reddifbackup.daily`, is installed for 14:00 local time.
The first eligible download attempt is November 9; today is suppressed. It requires
Brave to remain open with the debugging port and a valid mailbox session. Follow [PUSHKAR_GUIDE.md](PUSHKAR_GUIDE.md)
to resume and verify the archive.

## Delivery and repository state

The user selected local-only delivery. No Google Drive upload completed.
The local archive is under `backup_vault/`; these data files and credentials are
excluded from Git. The repository contains the tools, tests, and operating docs.
No password, session token, message body, or attachment is needed in GitHub.

## Automation estimate

At the observed 46 saved originals per successful quota window, 221 remaining
originals would require about five further runs. The server's actual daily quota
is unknown, so this is conditional. Ten Python tests pass, including scheduler
same-day suppression and browser-unavailable notification checks.

## Scheduler smoke-test result

The LaunchAgent was installed and registered, then explicitly smoke-tested.
macOS denied the scheduled Python interpreter access to the script in Downloads
(`Operation not permitted`). Automatic runs are therefore **not operational yet**.
User action in macOS Privacy & Security is required; see the guide. The intended
14:00 daily schedule will only work once that permission is granted and retested.
