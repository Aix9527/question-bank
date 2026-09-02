from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / 'apps' / 'api'
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.backup import backup_sqlite_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='创建专科复习在线题库 SQLite 一致性备份')
    parser.add_argument(
        '--database-url',
        default=os.getenv('QUESTION_BANK_DATABASE_URL', f"sqlite:///{(ROOT / 'apps' / 'api' / 'question_bank.db').as_posix()}"),
    )
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    target = args.output or ROOT / 'backups' / f"question-bank-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    result = backup_sqlite_database(args.database_url, target)
    payload = result.read_bytes()
    print(f'backup={result}')
    print(f'size={len(payload)}')
    print(f'sha256={hashlib.sha256(payload).hexdigest()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
