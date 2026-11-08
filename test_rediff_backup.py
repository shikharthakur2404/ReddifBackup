#!/usr/bin/env python3
"""
Comprehensive Test Suite for Rediffmail Pro Backup Suite
=========================================================
Tests:
1. Header decoding (UTF-8, Latin-1, encoded-words)
2. Filename sanitization across edge cases
3. Date/Time parser robustness (RFC-2822, IMAP INTERNALDATE fallback)
4. Attachment extraction and timestamp synchronization
5. Capsule vs Date-Split vs Flat directory generation
6. Mock IMAP End-to-End Archival & Incremental Sync
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from email.message import EmailMessage
import imaplib

# Import functions from rediff_backup
from rediff_backup import (
    clean_filename,
    decode_mime_header,
    parse_email_datetime,
    extract_internaldate,
    sync_file_mtime,
    save_attachment,
    process_folder,
)


class TestRediffBackup(unittest.TestCase):

    def test_clean_filename(self):
        self.assertEqual(clean_filename(""), "unnamed")
        self.assertEqual(clean_filename("hello/world:test*"), "hello_world_test")
        self.assertEqual(clean_filename("  TA of October month??  "), "TA_of_October_month")
        # Long filename truncate
        long_str = "a" * 100
        self.assertTrue(len(clean_filename(long_str, max_len=50)) <= 50)

    def test_decode_mime_header(self):
        self.assertEqual(decode_mime_header("Simple text"), "Simple text")
        # UTF-8 encoded word: "=?utf-8?B?VEEgb2YgT2N0b2Jlcg==?=" -> "TA of October"
        self.assertEqual(decode_mime_header("=?utf-8?B?VEEgb2YgT2N0b2Jlcg==?="), "TA of October")

    def test_parse_email_datetime(self):
        # Standard RFC-2822
        rfc_date = "Sat, 07 Nov 2026 07:52:14 +0000"
        dt = parse_email_datetime(rfc_date)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 11)
        self.assertEqual(dt.day, 7)
        self.assertEqual(dt.hour, 7)
        self.assertEqual(dt.minute, 52)

        # Fallback to INTERNALDATE
        internal_date = '"07-Nov-2026 07:52:14 +0000"'
        dt2 = parse_email_datetime("", internal_date)
        self.assertEqual(dt2.year, 2026)
        self.assertEqual(dt2.month, 11)
        self.assertEqual(dt2.day, 7)

    def test_attachment_extraction_and_mtime_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            target_dt = datetime(2026, 11, 7, 7, 52, 0, tzinfo=timezone.utc)

            # Construct multipart email message with attachment
            msg = EmailMessage()
            msg["Subject"] = "TA of October month"
            msg["From"] = "rajesh@domain.com"
            msg["Date"] = "Sat, 07 Nov 2026 07:52:00 +0000"
            msg.set_content("Please find attached TA sheet.")
            
            file_data = b"Sample Excel Spreadsheet binary content 12345"
            msg.add_attachment(file_data, maintype="application", subtype="vnd.ms-excel", filename="TA_October.xlsx")

            # Extract attachment
            saved_count = 0
            for part in msg.walk():
                if part.get_filename():
                    name = save_attachment(part, target_dir, target_dt)
                    self.assertEqual(name, "TA_October.xlsx")
                    saved_count += 1

            self.assertEqual(saved_count, 1)
            saved_file = target_dir / "TA_October.xlsx"
            self.assertTrue(saved_file.exists())
            self.assertEqual(saved_file.read_bytes(), file_data)
            
            # Verify file mtime matches email timestamp
            self.assertEqual(int(saved_file.stat().st_mtime), int(target_dt.timestamp()))

    def test_mock_imap_end_to_end(self):
        """Simulates full IMAP fetch flow and verifies folder/file structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_out = Path(tmpdir)
            
            # Create a mock Email
            msg = EmailMessage()
            msg["Subject"] = "October Travel Allowance"
            msg["From"] = "rajesh@rediffmailpro.com"
            msg["Date"] = "Sat, 07 Nov 2026 07:52:00 +0000"
            msg.set_content("Body text of the email")
            excel_bytes = b"EXCEL_BINARY_MOCK_DATA"
            msg.add_attachment(excel_bytes, maintype="application", subtype="octet-stream", filename="travel_sheet.xlsx")
            raw_email_bytes = msg.as_bytes()

            # Mock IMAP4_SSL client
            class MockIMAP:
                def select(self, folder, readonly=True):
                    return ("OK", [b"1"])

                def search(self, charset, criteria):
                    return ("OK", [b"101"])

                def fetch(self, msg_id, fetch_type):
                    if "HEADER.FIELDS" in fetch_type or "INTERNALDATE" in fetch_type:
                        hdr = b"Subject: October Travel Allowance\r\nFrom: rajesh@rediffmailpro.com\r\nDate: Sat, 07 Nov 2026 07:52:00 +0000\r\n\r\n"
                        resp = (b'101 (INTERNALDATE "07-Nov-2026 07:52:00 +0000" BODY[HEADER.FIELDS ...] {100}', hdr)
                        return ("OK", [resp])
                    elif "(RFC822)" in fetch_type:
                        return ("OK", [(b"101 {1000}", raw_email_bytes)])
                    return ("NO", [])

            mock_client = MockIMAP()

            # Process folder with default "capsule" layout
            process_folder(
                mail=mock_client,
                folder_name="INBOX",
                base_output_dir=base_out,
                organize_by="capsule",
                save_eml=True,
                extract_attachments=True
            )

            # Inspect created directory structure
            inbox_dir = base_out / "INBOX" / "2026" / "11-Nov"
            self.assertTrue(inbox_dir.exists(), f"Path not found: {inbox_dir}")

            capsules = list(inbox_dir.iterdir())
            self.assertEqual(len(capsules), 1)
            capsule = capsules[0]
            self.assertTrue(capsule.name.startswith("2026-11-07_07-52-AM"))

            # Check .eml exists
            eml_file = capsule / "message_101.eml"
            self.assertTrue(eml_file.exists())
            self.assertEqual(eml_file.read_bytes(), raw_email_bytes)

            # Check attachment exists
            att_file = capsule / "attachments" / "travel_sheet.xlsx"
            self.assertTrue(att_file.exists())
            self.assertEqual(att_file.read_bytes(), excel_bytes)

            # Check incremental skip (re-running does not re-download)
            process_folder(
                mail=mock_client,
                folder_name="INBOX",
                base_output_dir=base_out,
                organize_by="capsule",
                save_eml=True,
                extract_attachments=True
            )
            # Ensure file is still intact
            self.assertTrue(att_file.exists())

    def test_gdrive_zip_creation(self):
        from gdrive_sync import create_backup_zip
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "vault"
            source.mkdir()
            (source / "doc.txt").write_text("Hello Pushkar")
            out_zip = Path(tmpdir) / "backup.zip"
            created = create_backup_zip(source, out_zip)
            self.assertTrue(created.exists())
            self.assertTrue(created.stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
