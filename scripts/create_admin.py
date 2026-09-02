from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / 'apps' / 'api'
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select  # noqa: E402
from app.db import Base, build_engine, build_session_factory  # noqa: E402
from app.models import ai_review, attempt, core, import_job, learning, question_bank, review, user as user_models  # noqa: F401,E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import create_user, hash_password  # noqa: E402
from app.services.bootstrap import seed_subjects, seed_users  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Create or reset a question-bank administrator.')
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', help='Password; omit to enter it securely at the prompt.')
    parser.add_argument('--display-name', default='管理员')
    args = parser.parse_args()
    password = args.password or getpass.getpass('Admin password: ')
    if len(password) < 8:
        parser.error('password must be at least 8 characters')

    engine = build_engine(); Base.metadata.create_all(engine); factory = build_session_factory(engine)
    with factory() as session:
        seed_subjects(session); seed_users(session, admin_username=None, admin_password=None)
        existing = session.scalar(select(User).where(User.username == args.username))
        if existing is None:
            created = create_user(session, username=args.username, password=password, display_name=args.display_name, role='admin')
            print(f'created admin id={created.id} username={created.username}')
        else:
            existing.role = 'admin'; existing.enabled = True; existing.display_name = args.display_name; existing.password_hash = hash_password(password)
            session.commit(); print(f'updated admin id={existing.id} username={existing.username}')
    engine.dispose(); return 0


if __name__ == '__main__':
    raise SystemExit(main())
