from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def integrity_ok(path: Path) -> bool:
    try:
        with sqlite3.connect(path) as con:
            result = con.execute('PRAGMA integrity_check').fetchone()
            return bool(result and result[0] == 'ok')
    except sqlite3.Error:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description='Safely restore a SQLite question-bank backup.')
    parser.add_argument('backup', type=Path)
    parser.add_argument('--target', type=Path, default=Path('question_bank.db'))
    parser.add_argument('--force', action='store_true', help='Required when target already exists.')
    args = parser.parse_args()
    if not args.backup.is_file() or not integrity_ok(args.backup):
        parser.error('backup is missing or failed SQLite integrity_check')
    target = args.target.resolve(); target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not args.force:
        parser.error('target exists; pass --force to replace it')
    if target.exists():
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        safety = target.with_name(f'{target.name}.pre-restore-{stamp}.bak')
        shutil.copy2(target, safety)
        print(f'current database copied to {safety}')
    temp = target.with_suffix(target.suffix + '.restore-tmp')
    shutil.copy2(args.backup, temp)
    if not integrity_ok(temp):
        temp.unlink(missing_ok=True); parser.error('copied database failed integrity_check')
    temp.replace(target)
    print(f'restored {args.backup} -> {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
