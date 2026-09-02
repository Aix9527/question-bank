import sqlite3


def test_sqlite_backup_is_consistent_copy(tmp_path):
    from app.services.backup import backup_sqlite_database

    source = tmp_path / 'source.db'
    with sqlite3.connect(source) as conn:
        conn.execute('create table demo (value text)')
        conn.execute("insert into demo values ('ok')")
        conn.commit()

    destination = tmp_path / 'backup.db'
    result = backup_sqlite_database(f'sqlite:///{source}', destination)

    assert result == destination
    with sqlite3.connect(destination) as conn:
        assert conn.execute('select value from demo').fetchone()[0] == 'ok'


def test_admin_database_backup_endpoint_returns_sqlite_snapshot(client):
    response = client.get('/api/admin/backup/database')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/vnd.sqlite3')
    assert response.content.startswith(b'SQLite format 3')
