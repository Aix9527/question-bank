from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db import Base

# 必须与 alembic/env.py 保持一致，确保 Base.metadata 注册完整 15 张表。
from app.models import ai_review  # noqa: F401
from app.models import attempt  # noqa: F401
from app.models import core  # noqa: F401
from app.models import import_job  # noqa: F401
from app.models import learning  # noqa: F401
from app.models import question_bank  # noqa: F401
from app.models import review  # noqa: F401
from app.models import user  # noqa: F401


# ---------------------------------------------------------------------------
# Frozen migration contract
# ---------------------------------------------------------------------------

EXPECTED_BASELINE_REVISION = "b745d0dc0c47"

# 已核验的 question-bank-v0.5-final.db SHA256。
EXPECTED_SOURCE_SHA256 = (
    "32f30b13ea034ab4bcc45ccd59539d65"
    "c1cddc0331de14333fb7f41d607d2f55"
)

SOURCE_RELATIVE_PATH = (
    Path("release-v0.5-final")
    / "question-bank-v0.5-final.db"
)

# v0.5 Final 实际冻结数据。
EXPECTED_COUNTS: dict[str, int] = {
    "subjects": 3,
    "users": 2,
    "papers": 6,
    "questions": 188,
    "question_options": 667,
    "paper_sections": 26,
    "paper_questions": 188,
    "attempts": 0,
    "answer_records": 0,
    "wrong_questions": 0,
    "favorites": 0,
    "import_jobs": 6,
    "user_sessions": 7,
    "ai_review_suggestions": 0,
    "manual_reviews": 0,
}

EXPECTED_TABLES = frozenset(EXPECTED_COUNTS)

# v0.6 明确暂不建立 users FK 的 4 个字段。
# Schema 不加 FK，但迁移时仍检查语义孤儿。
SEMANTIC_USER_REFS = (
    ("attempts", "user_id"),
    ("wrong_questions", "user_id"),
    ("favorites", "user_id"),
    ("manual_reviews", "reviewer_user_id"),
)


class MigrationError(RuntimeError):
    """Hard migration gate failure."""


# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_source_db() -> Path:
    """
    不接受任意 --source。

    只允许固定文件：
      release-v0.5-final/question-bank-v0.5-final.db

    支持：
      1. <repo>/release-v0.5-final/...
      2. 当前 TRAE work-mode 目录：
         <work-mode-project>/release-v0.5-final/...
    """
    script_path = Path(__file__).resolve()
    # <repo>/apps/api/scripts/migrate_sqlite_to_pg.py
    repo_root = script_path.parents[3]
    candidates = [
        repo_root / SOURCE_RELATIVE_PATH,
    ]
    # 当前实际目录：
    # <work-mode-project>/release-v0.5-final 与 <repo> 平级
    # repo_root.parents[1] == <work-mode-project>（repo 在 v0.5 子目录下）
    if len(repo_root.parents) >= 2:
        candidates.append(repo_root.parents[1] / SOURCE_RELATIVE_PATH)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_candidates.append(resolved)

    existing = [path for path in unique_candidates if path.is_file()]
    if not existing:
        raise MigrationError(
            "Frozen source DB not found. Expected one of:\n  - "
            + "\n  - ".join(str(path) for path in unique_candidates)
        )

    verified: list[Path] = []
    mismatches: list[str] = []
    for path in existing:
        actual_sha = sha256_file(path)
        if actual_sha.lower() == EXPECTED_SOURCE_SHA256.lower():
            verified.append(path)
        else:
            mismatches.append(f"{path}: {actual_sha}")

    if not verified:
        raise MigrationError(
            "Frozen source DB SHA256 mismatch.\n"
            f"Expected: {EXPECTED_SOURCE_SHA256}\n"
            "Found:\n  - " + "\n  - ".join(mismatches)
        )

    # 若 repo-local 和 TRAE workspace 两份都存在且哈希一致，按候选顺序固定使用第一份。
    return verified[0]


def open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    # 二次保护：即使未来代码误执行写 SQL，也禁止写入。
    connection.execute("PRAGMA query_only = ON")
    return connection


def sqlite_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {str(row["name"]) for row in rows}


def sqlite_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {str(row["name"]) for row in rows}


def sqlite_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f'SELECT COUNT(*) AS n FROM "{table_name}"').fetchone()
    return int(row["n"])


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------

def metadata_tables() -> list[sa.Table]:
    """必须直接使用 Base.metadata.sorted_tables。"""
    tables = list(Base.metadata.sorted_tables)
    names = frozenset(table.name for table in tables)
    if names != EXPECTED_TABLES:
        raise MigrationError(
            "Base.metadata mismatch: "
            f"missing={sorted(EXPECTED_TABLES - names)}, "
            f"extra={sorted(names - EXPECTED_TABLES)}"
        )
    if len(tables) != 15:
        raise MigrationError(f"Expected 15 metadata tables, got {len(tables)}")
    return tables


# ---------------------------------------------------------------------------
# Source gates
# ---------------------------------------------------------------------------

def validate_source(
    conn: sqlite3.Connection,
    tables: list[sa.Table],
) -> dict[str, int]:
    # SQLite physical integrity
    integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    if integrity.lower() != "ok":
        raise MigrationError(f"SQLite integrity_check failed: {integrity}")

    # SQLite declared FK integrity
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        preview = [tuple(row) for row in fk_errors[:20]]
        raise MigrationError(
            "SQLite foreign_key_check failed: "
            f"{len(fk_errors)} error(s), "
            f"preview={preview}"
        )

    source_tables = sqlite_table_names(conn)
    missing_tables = sorted(EXPECTED_TABLES - source_tables)
    if missing_tables:
        raise MigrationError(f"SQLite source missing tables: {missing_tables}")

    # 每张源表必须与当前模型列集合一致。
    for table in tables:
        source_cols = sqlite_columns(conn, table.name)
        model_cols = {column.name for column in table.columns}
        if source_cols != model_cols:
            missing_cols = sorted(model_cols - source_cols)
            extra_cols = sorted(source_cols - model_cols)
            raise MigrationError(
                f"SQLite columns mismatch for {table.name}: "
                f"missing={missing_cols}, extra={extra_cols}"
            )

    counts = {
        table.name: sqlite_count(conn, table.name)
        for table in tables
    }

    count_failures = {
        table_name: {"actual": counts[table_name], "expected": expected}
        for table_name, expected in EXPECTED_COUNTS.items()
        if counts[table_name] != expected
    }
    if count_failures:
        raise MigrationError(
            "Frozen source count gate failed: "
            + json.dumps(count_failures, ensure_ascii=False, sort_keys=True)
        )

    users = conn.execute(
        """
        SELECT id, username
        FROM users
        ORDER BY id
        """
    ).fetchall()
    actual_users = [(int(row["id"]), str(row["username"])) for row in users]
    expected_users = [(1, "admin"), (2, "bob")]
    if actual_users != expected_users:
        raise MigrationError(
            "SQLite user gate failed: "
            f"actual={actual_users}, expected={expected_users}"
        )

    return counts


# ---------------------------------------------------------------------------
# Target helpers / gates
# ---------------------------------------------------------------------------

def validate_migration_url(value: str | None) -> str:
    if not value:
        raise MigrationError("DATABASE_MIGRATION_URL is required.")
    try:
        url = make_url(value)
    except Exception as exc:
        raise MigrationError("DATABASE_MIGRATION_URL could not be parsed.") from exc
    if url.get_backend_name() != "postgresql":
        raise MigrationError("DATABASE_MIGRATION_URL must use PostgreSQL.")
    if url.port != 5432:
        raise MigrationError(
            "DATABASE_MIGRATION_URL must use Supabase Session Pooler :5432; "
            f"got port={url.port!r}."
        )
    return value


def pg_count(conn: Connection, table_name: str) -> int:
    return int(
        conn.execute(text(f'SELECT COUNT(*) FROM public."{table_name}"')).scalar_one()
    )


def get_sequence(conn: Connection, table_name: str) -> str:
    sequence = conn.execute(
        text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
        {"table_name": f"public.{table_name}"},
    ).scalar_one_or_none()
    if not sequence:
        raise MigrationError(f"No id sequence for public.{table_name}")
    return str(sequence)


def validate_target_preflight(conn: Connection, tables: list[sa.Table]) -> None:
    inspector = inspect(conn)
    public_tables = set(inspector.get_table_names(schema="public"))
    required_tables = set(EXPECTED_TABLES) | {"alembic_version"}
    missing = sorted(required_tables - public_tables)
    if missing:
        raise MigrationError(f"Supabase baseline tables missing: {missing}")

    revisions = conn.execute(
        text("SELECT version_num FROM public.alembic_version ORDER BY version_num")
    ).scalars().all()
    if revisions != [EXPECTED_BASELINE_REVISION]:
        raise MigrationError(
            "Alembic revision mismatch: "
            f"actual={revisions}, expected={[EXPECTED_BASELINE_REVISION]}"
        )

    # 15 张应用表必须全部为空。
    nonempty: dict[str, int] = {}
    for table in tables:
        count = pg_count(conn, table.name)
        if count != 0:
            nonempty[table.name] = count
    if nonempty:
        raise MigrationError(
            "Target application tables are not empty: "
            + json.dumps(nonempty, sort_keys=True)
        )

    # baseline 建出来的 15 个 SERIAL sequence 也必须全部存在。
    for table in tables:
        get_sequence(conn, table.name)


# ---------------------------------------------------------------------------
# Data conversion
# ---------------------------------------------------------------------------

def convert_json(value: Any, *, table_name: str, column_name: str, row_id: Any) -> Any:
    if value is None:
        return None
    # SQLite SQLAlchemy JSON 通常落为 TEXT。
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise MigrationError(
                "Invalid JSON TEXT at "
                f"{table_name}.{column_name}, id={row_id!r}: {exc}"
            ) from exc
    # 防御性支持 SQLite BLOB。
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            decoded = bytes(value).decode("utf-8")
            return json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MigrationError(
                "Invalid JSON bytes at "
                f"{table_name}.{column_name}, id={row_id!r}: {exc}"
            ) from exc
    # JSON scalar
    if isinstance(value, (int, float, bool, list, dict)):
        return value
    raise MigrationError(
        "Unsupported JSON value at "
        f"{table_name}.{column_name}, id={row_id!r}: {type(value).__name__}"
    )


def load_rows(source: sqlite3.Connection, table: sa.Table) -> list[dict[str, Any]]:
    rows = source.execute(
        f'SELECT * FROM "{table.name}" ORDER BY id'
    ).fetchall()
    json_columns = {
        column.name
        for column in table.columns
        if isinstance(column.type, sa.JSON)
    }
    payload: list[dict[str, Any]] = []
    for row in rows:
        raw = dict(row)
        row_id = raw.get("id")
        # 显式携带所有模型列，包括历史 PK id，不由 PG sequence 重新分配主键。
        item = {column.name: raw[column.name] for column in table.columns}
        for column_name in json_columns:
            item[column_name] = convert_json(
                item[column_name],
                table_name=table.name,
                column_name=column_name,
                row_id=row_id,
            )
        # Boolean / DateTime 故意不手工转换，原值交给 SQLAlchemy column type。
        payload.append(item)
    return payload


# ---------------------------------------------------------------------------
# Integrity checks
# ---------------------------------------------------------------------------

def validate_semantic_user_refs(conn: Connection) -> None:
    failures: list[str] = []
    for table_name, column_name in SEMANTIC_USER_REFS:
        orphan_count = int(
            conn.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM public."{table_name}" AS child
                    LEFT JOIN public.users AS u
                      ON u.id = child."{column_name}"
                    WHERE child."{column_name}" IS NOT NULL
                      AND u.id IS NULL
                    """
                )
            ).scalar_one()
        )
        if orphan_count:
            failures.append(f"{table_name}.{column_name}={orphan_count}")
    if failures:
        raise MigrationError(
            "Semantic user-reference orphan gate failed: " + ", ".join(failures)
        )


# ---------------------------------------------------------------------------
# Sequence reset / validation
# ---------------------------------------------------------------------------

def reset_sequence(conn: Connection, table_name: str) -> None:
    sequence = get_sequence(conn, table_name)
    max_id = conn.execute(
        text(f'SELECT MAX(id) FROM public."{table_name}"')
    ).scalar_one()
    if max_id is None:
        # 空表：下一次 nextval() 返回 1。
        conn.execute(
            text("SELECT setval(CAST(:sequence_name AS regclass), 1, false)"),
            {"sequence_name": sequence},
        )
    else:
        # 非空表：sequence = MAX(id)，下一次 nextval() 返回 MAX(id)+1。
        conn.execute(
            text("SELECT setval(CAST(:sequence_name AS regclass), :max_id, true)"),
            {"sequence_name": sequence, "max_id": int(max_id)},
        )


def validate_sequences(conn: Connection, tables: list[sa.Table]) -> None:
    failures: list[str] = []
    for table in tables:
        sequence = get_sequence(conn, table.name)
        max_id = conn.execute(
            text(f'SELECT MAX(id) FROM public."{table.name}"')
        ).scalar_one()
        sequence_name = sequence.rsplit(".", 1)[-1]
        last_value = conn.execute(
            text(
                """
                SELECT last_value
                FROM pg_sequences
                WHERE schemaname = 'public'
                  AND sequencename = :sequence_name
                """
            ),
            {"sequence_name": sequence_name},
        ).scalar_one_or_none()
        if max_id is None:
            # 空表：序列尚未被 nextval 使用过时 PG 返回 last_value=NULL，
            # 这是正常状态（setval(...,1,false) 已保证下一个 nextval 返回 1）。
            if last_value is not None and int(last_value) < 1:
                failures.append(
                    f"{table.name}: empty table but sequence last_value={last_value} < 1"
                )
        else:
            expected_last = int(max_id)
            if last_value is None or int(last_value) < expected_last:
                failures.append(
                    f"{table.name}: max_id={max_id}, sequence={sequence}, "
                    f"last_value={last_value}, expected>={expected_last}"
                )
    if failures:
        raise MigrationError("Sequence validation failed:\n  - " + "\n  - ".join(failures))


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

def print_count_report(
    sqlite_counts: dict[str, int],
    pg_counts: dict[str, int],
    tables: list[sa.Table],
) -> None:
    print()
    print("COUNT REPORT")
    print("-" * 62)
    print(f"{'TABLE':24} {'SQLITE':>10} {'POSTGRES':>10} {'RESULT':>8}")
    print("-" * 62)
    failures: list[str] = []
    for table in tables:
        table_name = table.name
        sqlite_n = sqlite_counts[table_name]
        pg_n = pg_counts[table_name]
        passed = sqlite_n == pg_n == EXPECTED_COUNTS[table_name]
        print(
            f"{table_name:24} {sqlite_n:10d} {pg_n:10d} "
            f"{'PASS' if passed else 'FAIL':>8}"
        )
        if not passed:
            failures.append(table_name)
    print("-" * 62)
    if failures:
        print("COUNT GATE = FAIL")
        raise MigrationError(f"Count gate failed for: {failures}")
    print("COUNT GATE = PASS")


# ---------------------------------------------------------------------------
# Main migration
# ---------------------------------------------------------------------------

def run() -> None:
    # 1. Freeze current SQLAlchemy metadata contract
    tables = metadata_tables()
    print("METADATA TABLES =", len(tables))
    print("METADATA GATE = PASS")

    # 2. Locate + verify frozen SQLite
    source_path = resolve_source_db()
    source_sha = sha256_file(source_path)
    print()
    print("SOURCE =", source_path)
    print("SOURCE SHA256 =", source_sha)
    print("SOURCE SHA256 GATE = PASS")

    source = open_sqlite_readonly(source_path)
    try:
        source_counts = validate_source(source, tables)
        print("SOURCE INTEGRITY GATE = PASS")
        print("SOURCE FK GATE = PASS")
        print("SOURCE FROZEN-COUNT GATE = PASS")
        print("SOURCE USER GATE = PASS")

        # 3. Connect only through DATABASE_MIGRATION_URL :5432
        settings = get_settings()
        migration_url = validate_migration_url(settings.database_migration_url)
        engine = sa.create_engine(
            migration_url,
            poolclass=NullPool,
            pool_pre_ping=True,
            future=True,
        )
        try:
            with engine.connect() as target:
                transaction = target.begin()
                try:
                    # 所有无 schema Table INSERT 固定落到 public。
                    target.execute(text("SET LOCAL search_path TO public"))

                    # 4. Target baseline + empty second protection
                    validate_target_preflight(target, tables)
                    print()
                    print("TARGET BASELINE GATE = PASS")
                    print("TARGET EMPTY GATE = PASS")
                    print("TARGET SEQUENCE PRECHECK = PASS")

                    # 5. INSERT in Base.metadata.sorted_tables order
                    print()
                    print("COPY")
                    for table in tables:
                        payload = load_rows(source, table)
                        if payload:
                            # 每一行都显式包含 id，保留 SQLite 历史 PK。
                            target.execute(table.insert(), payload)
                        inserted = pg_count(target, table.name)
                        expected = source_counts[table.name]
                        if inserted != expected:
                            raise MigrationError(
                                f"{table.name} count mismatch immediately after insert: "
                                f"sqlite={expected}, pg={inserted}"
                            )
                        print(f"PASS  {table.name:24} {inserted}")

                    # 6. Semantic orphan gate for deferred user FKs
                    validate_semantic_user_refs(target)
                    print("SEMANTIC USER-REFERENCE ORPHANS = 0")

                    # 7. Row counts before sequence operations
                    pg_counts = {
                        table.name: pg_count(target, table.name)
                        for table in tables
                    }
                    print_count_report(source_counts, pg_counts, tables)

                    # 8. admin / bob hard gate
                    target_users = [
                        (int(row[0]), str(row[1]))
                        for row in target.execute(
                            text(
                                """
                                SELECT id, username
                                FROM public.users
                                ORDER BY id
                                """
                            )
                        ).all()
                    ]
                    if target_users != [(1, "admin"), (2, "bob")]:
                        raise MigrationError(f"Target user gate failed: {target_users}")
                    print("TARGET USER GATE = PASS")

                    # 9. Reset all 15 SERIAL sequences
                    print()
                    print("RESET SEQUENCES")
                    for table in tables:
                        reset_sequence(target, table.name)
                        print(f"PASS  {table.name}")
                    validate_sequences(target, tables)
                    print("SEQUENCE DRIFT = 0")

                    # 10. Final counts while transaction is still open
                    final_pg_counts = {
                        table.name: pg_count(target, table.name)
                        for table in tables
                    }
                    print_count_report(source_counts, final_pg_counts, tables)
                    print()
                    print("ALL HARD GATES = PASS")
                    print("COMMITTING TRANSACTION ...")
                    transaction.commit()
                except Exception:
                    if transaction.is_active:
                        transaction.rollback()
                    print("TRANSACTION = ROLLBACK", file=sys.stderr)
                    raise
            print()
            print("TRANSACTION = COMMIT")
            print("DATA MIGRATION GATE = PASS")
        finally:
            engine.dispose()
    finally:
        source.close()


def main() -> int:
    try:
        run()
    except Exception as exc:
        print("\nDATA MIGRATION GATE = FAIL", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
