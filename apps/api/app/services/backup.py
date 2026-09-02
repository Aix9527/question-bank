from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.engine import make_url


def sqlite_database_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
        raise ValueError('SQLite file database required')
    return Path(url.database).expanduser().resolve()


def backup_sqlite_database(database_url: str, destination: Path) -> Path:
    source = sqlite_database_path(database_url)
    if not source.exists():
        raise FileNotFoundError(source)
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return destination


def backup_sqlite_bytes(database_url: str) -> bytes:
    with TemporaryDirectory(prefix='question-bank-backup-') as tmpdir:
        target = Path(tmpdir) / 'question-bank-backup.db'
        backup_sqlite_database(database_url, target)
        return target.read_bytes()
