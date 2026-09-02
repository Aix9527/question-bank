from __future__ import annotations

import base64
import hashlib
import html
from pathlib import Path
from typing import Any

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def _image_tags(paragraph: Paragraph) -> tuple[list[str], int]:
    tags: list[str] = []
    count = 0
    for run in paragraph.runs:
        for blip in run._r.xpath('.//a:blip'):
            rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if not rid:
                continue
            part = paragraph.part.related_parts.get(rid)
            if part is None or not hasattr(part, 'blob'):
                continue
            blob = part.blob
            mime = getattr(part, 'content_type', 'application/octet-stream')
            digest = hashlib.sha256(blob).hexdigest()
            encoded = base64.b64encode(blob).decode('ascii')
            tags.append(
                f'<img src="data:{html.escape(mime, quote=True)};base64,{encoded}" '
                f'data-source-sha256="{digest}" alt="DOCX内嵌图片" />'
            )
            count += 1
    return tags, count


def _paragraph_payload(paragraph: Paragraph, index: int) -> tuple[dict[str, Any], int]:
    text = paragraph.text or ''
    math_texts = [node.text or '' for node in paragraph._p.xpath('.//m:t')]
    math_text = ''.join(math_texts).strip()
    if math_text and math_text not in text:
        text = f'{text}{math_text}'

    image_tags, image_count = _image_tags(paragraph)
    fragments: list[str] = []
    if text:
        fragments.append(html.escape(text).replace('\n', '<br>'))
    fragments.extend(image_tags)
    unsupported = len(paragraph._p.xpath('.//w:object'))

    return {
        'kind': 'paragraph',
        'index': index,
        'style': paragraph.style.name if paragraph.style is not None else None,
        'text': text,
        'html': ''.join(fragments),
        'rows': None,
        'equation_text': math_text or None,
        'unsupported_object_count': unsupported,
    }, image_count


def _table_payload(table: Table, index: int) -> dict[str, Any]:
    rows = [[cell.text for cell in row.cells] for row in table.rows]
    html_rows = []
    for row in rows:
        cells = ''.join(f'<td>{html.escape(cell).replace(chr(10), "<br>")}</td>' for cell in row)
        html_rows.append(f'<tr>{cells}</tr>')
    return {
        'kind': 'table',
        'index': index,
        'style': getattr(table.style, 'name', None),
        'text': '\n'.join('\t'.join(row) for row in rows),
        'html': f'<table>{"".join(html_rows)}</table>',
        'rows': rows,
        'equation_text': None,
        'unsupported_object_count': 0,
    }


def parse_docx(path: Path) -> dict[str, Any]:
    path = Path(path)
    raw = path.read_bytes()
    document = Document(path)
    blocks: list[dict[str, Any]] = []
    media_count = 0
    unsupported_count = 0

    for index, block in enumerate(document.iter_inner_content()):
        if isinstance(block, Paragraph):
            payload, images = _paragraph_payload(block, index)
            media_count += images
            unsupported_count += payload['unsupported_object_count']
            blocks.append(payload)
        elif isinstance(block, Table):
            blocks.append(_table_payload(block, index))

    return {
        'source_filename': path.name,
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'source_size': len(raw),
        'media_count': media_count,
        'unsupported_object_count': unsupported_count,
        'blocks': blocks,
    }
