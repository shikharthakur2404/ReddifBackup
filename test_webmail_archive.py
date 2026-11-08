import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from extract_webmail import extract


class WebmailExtractionTests(unittest.TestCase):
    def fixture(self, root):
        msg = EmailMessage()
        msg['From'] = 'sender@example.org'
        msg['Subject'] = 'Archive fixture'
        msg.set_content('Body')
        for data in (b'first\x00\xff', b'second\x00\xfe'):
            msg.add_attachment(data, maintype='application', subtype='octet-stream', filename='../../same.bin')
        data = msg.as_bytes()
        (root / 'message.eml').write_bytes(data)
        manifest = {'originals_complete': True, 'folders': {'Inbox': {'total': 1}},
                    'messages': {'Inbox/id': {'path': 'message.eml', 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(), 'date': '2026-04-01T12:00:00.000Z',
                    'attachment_expected': True}}}
        (root / 'manifest.json').write_text(json.dumps(manifest))

    def run_extract(self, root):
        with contextlib.redirect_stdout(io.StringIO()):
            return extract(root)

    def test_binary_duplicate_names_safe_and_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            report = self.run_extract(root)
            self.assertTrue(report['verified'])
            files = report['messages'][0]['attachments']
            self.assertEqual(len(files), 2)
            self.assertNotEqual(files[0]['path'], files[1]['path'])
            self.assertEqual((root / files[0]['path']).read_bytes(), b'first\x00\xff')
            for f in files:
                self.assertEqual((root / f['path']).resolve().parent, (root / 'attachments').resolve())
            self.assertEqual(self.run_extract(root)['attachments'], 2)
            self.assertEqual(len(list((root / 'attachments').iterdir())), 2)

    def test_corrupt_original_is_not_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with (root / 'message.eml').open('ab') as stream:
                stream.write(b'corruption')
            report = self.run_extract(root)
            self.assertFalse(report['verified'])
            self.assertEqual(report['attachments'], 0)
            self.assertIn('checksum mismatch', report['errors'][0])


if __name__ == '__main__':
    unittest.main()
