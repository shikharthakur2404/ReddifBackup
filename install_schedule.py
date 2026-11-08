#!/usr/bin/env python3
"""Install a macOS per-user daily backup job at 14:00 local time."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent
LABEL = 'com.reddifbackup.daily'


def configuration():
    return {'Label': LABEL,
            'ProgramArguments': [sys.executable, str(ROOT / 'scheduled_backup.py')],
            'WorkingDirectory': str(ROOT),
            'EnvironmentVariables': {'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'},
            'StartCalendarInterval': {'Hour': 14, 'Minute': 0},
            'RunAtLoad': False,
            'StandardOutPath': str(ROOT / 'logs/scheduler.log'),
            'StandardErrorPath': str(ROOT / 'logs/scheduler-error.log')}


if __name__ == '__main__':
    if '--install' not in sys.argv:
        sys.stdout.buffer.write(plistlib.dumps(configuration()))
    else:
        logs = ROOT / 'logs'
        logs.mkdir(exist_ok=True)
        state = logs / 'schedule_state.json'
        # Do not retry today's known exhausted quota immediately after installation.
        if not state.exists():
            state.write_text(json.dumps({'last_attempt_date': datetime.now().strftime('%Y-%m-%d')}) + '\n')
        destination = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
        destination.parent.mkdir(parents=True, exist_ok=True)
        config = configuration()
        if destination.exists() and plistlib.loads(destination.read_bytes()) != config:
            raise SystemExit('Existing schedule differs; inspect it before replacing it.')
        destination.write_bytes(plistlib.dumps(config))
        domain = 'gui/' + str(os.getuid())
        exists = subprocess.run(['launchctl', 'print', domain + '/' + LABEL], capture_output=True)
        if exists.returncode:
            subprocess.run(['launchctl', 'bootstrap', domain, str(destination)], check=True)
        subprocess.run(['launchctl', 'print', domain + '/' + LABEL], check=True)
