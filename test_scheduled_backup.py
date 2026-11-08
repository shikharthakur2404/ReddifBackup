import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import os

import scheduled_backup


class ScheduledBackupTests(unittest.TestCase):
    def test_does_not_retry_same_day(self):
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / 'logs').mkdir()
                (root / 'logs/schedule_state.json').write_text(json.dumps(
                    {'last_attempt_date': datetime.now().strftime('%Y-%m-%d')}))
                with patch.object(scheduled_backup, 'ROOT', root), patch.object(scheduled_backup, 'urlopen') as network:
                    self.assertEqual(scheduled_backup.main(), 0)
                    network.assert_not_called()
        finally:
            os.chdir(cwd)

    def test_browser_unavailable_notifies_without_download(self):
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as d:
                with patch.object(scheduled_backup, 'ROOT', Path(d)), \
                     patch.object(scheduled_backup.shutil, 'which', return_value='/usr/bin/node'), \
                     patch.object(scheduled_backup, 'urlopen', side_effect=ConnectionError), \
                     patch.object(scheduled_backup, 'notify') as notification, \
                     patch.object(scheduled_backup.subprocess, 'run') as run:
                    self.assertEqual(scheduled_backup.main(), 1)
                    notification.assert_called_once()
                    run.assert_not_called()
        finally:
            os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
