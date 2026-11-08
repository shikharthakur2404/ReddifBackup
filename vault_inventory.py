#!/usr/bin/env python3
"""Write a SHA-256 inventory of actual archived bytes, without claiming completeness."""
import argparse
import hashlib
import json
from collections import Counter
from email import policy
from email.parser import BytesParser
from pathlib import Path


def inventory(vault):
    records = []
    for path in sorted(vault.rglob('*')):
        if not path.is_file() or path.name.startswith('.') or path.name == 'inventory.json':
            continue
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        record = {'path': str(path.relative_to(vault)), 'bytes': path.stat().st_size,
                  'sha256': digest.hexdigest(),
                  'kind': 'eml' if path.suffix.lower() == '.eml' else
                          'attachment' if 'attachments' in path.relative_to(vault).parts else 'other'}
        if record['kind'] == 'eml':
            with path.open('rb') as stream:
                msg = BytesParser(policy=policy.default).parse(stream, headersonly=True)
            record.update(date=str(msg.get('Date', '')), message_id=str(msg.get('Message-ID', '')))
        records.append(record)
    return {'historical_completeness_verified': False,
            'counts': dict(Counter(r['kind'] for r in records)),
            'total_bytes': sum(r['bytes'] for r in records), 'files': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, default=Path('backup_vault'))
    args = parser.parse_args()
    if not args.vault.is_dir():
        parser.error('Vault directory does not exist')
    result = inventory(args.vault)
    output = args.vault / 'inventory.json'
    temp = output.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result, indent=2) + '\n')
    temp.replace(output)
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()
