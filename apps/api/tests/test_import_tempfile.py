from pathlib import Path


def test_parse_docx_bytes_closes_writer_before_parse_and_cleans_up(monkeypatch):
    from app.services.imports import publisher

    payload = b'fake-docx-bytes'
    seen_path: Path | None = None

    def fake_parse(path: Path):
        nonlocal seen_path
        seen_path = path
        # Path.read_bytes opens a fresh reader. The production helper must have
        # completed and closed its writer before invoking parse_docx.
        assert path.read_bytes() == payload
        return {'blocks': []}

    monkeypatch.setattr(publisher, 'parse_docx', fake_parse)

    ast = publisher._parse_docx_bytes(filename='sample.docx', data=payload)

    assert ast == {'blocks': []}
    assert seen_path is not None
    assert not seen_path.exists()
