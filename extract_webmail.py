#!/usr/bin/env python3
"""Verify archived originals and extract MIME attachments with stable names and hashes."""
import hashlib
import json
import os
import re
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(root=Path('backup_vault/Webmail')):
    manifest = json.loads((root / 'manifest.json').read_text())
    report = {'originals_complete': manifest.get('originals_complete', False),
              'messages': [], 'errors': [], 'attachments': 0, 'attachment_bytes': 0}
    expected = sum(f['total'] for f in manifest['folders'].values())
    if len(manifest['messages']) != expected:
        report['errors'].append(f"Expected {expected} messages, saved {len(manifest['messages'])}")
    for key, record in manifest['messages'].items():
        path = root / record['path']
        data = path.read_bytes()
        if len(data) != record['bytes'] or digest(data) != record['sha256']:
            report['errors'].append('Original checksum mismatch: ' + key)
            continue
        msg = BytesParser(policy=policy.default).parsebytes(data)
        result = {'key': key, 'date': record['date'], 'subject': str(msg.get('Subject', '')),
                  'sender': str(msg.get('From', '')), 'attachments': []}
        for index, part in enumerate(msg.walk()):
            if not part.get_filename() and part.get_content_disposition() != 'attachment':
                continue
            name = str(part.get_filename() or f'attachment_{index}')
            payload = part.get_payload(decode=True)
            if payload is None and part.get_content_type() == 'message/rfc822':
                payload = b'\n'.join(p.as_bytes() for p in part.get_payload())
            if payload is None:
                report['errors'].append(f'Undecodable attachment: {key} part {index}')
                continue
            if part.defects:
                report['errors'].append(f'MIME defect: {key} part {index}: {part.defects}')
            filename = f'{index:03d}_' + re.sub(r'[^\w. -]', '_', name)[:160]
            target = path.parent / 'attachments' / filename
            target.parent.mkdir(exist_ok=True)
            temp = target.with_name(target.name + '.part')
            temp.write_bytes(payload)
            temp.replace(target)
            timestamp = datetime.fromisoformat(record['date'].replace('Z', '+00:00')).timestamp()
            os.utime(target, (timestamp, timestamp))
            if digest(target.read_bytes()) != digest(payload):
                report['errors'].append('Attachment checksum mismatch: ' + str(target))
            result['attachments'].append({'name': name, 'path': str(target.relative_to(root)),
                                           'bytes': len(payload), 'sha256': digest(payload)})
            report['attachments'] += 1
            report['attachment_bytes'] += len(payload)
        if record['attachment_expected'] and not result['attachments']:
            report['errors'].append('Expected attachment missing: ' + key)
        report['messages'].append(result)
    report['verified'] = report['originals_complete'] and not report['errors']
    temp = root / 'verification.json.tmp'
    temp.write_text(json.dumps(report, indent=2) + '\n')
    temp.replace(root / 'verification.json')
    print(json.dumps({k: v for k, v in report.items() if k != 'messages'}, indent=2))
    return report


if __name__ == '__main__':
    raise SystemExit(0 if extract()['verified'] else 1)
