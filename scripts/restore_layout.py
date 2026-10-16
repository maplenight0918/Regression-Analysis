"""Restore the pre-purple front end, preserving the current version first."""
from pathlib import Path
from datetime import datetime
import shutil
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
snapshot=ROOT/'backups/layout-before-purple-20261016'
for name,digest in json.loads((snapshot/'manifest.json').read_text()).items():
    if hashlib.sha256((snapshot/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit(f'Snapshot checksum mismatch: {name}')
saved=ROOT/'backups'/('before-restore-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
saved.mkdir(parents=True)
shutil.copytree(ROOT/'static',saved/'static')
shutil.copytree(snapshot/'static',ROOT/'static',dirs_exist_ok=True)
print(f'Original layout restored. Previous version preserved at {saved}. Refresh your browser.')
