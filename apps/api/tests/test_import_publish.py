from __future__ import annotations

import io

from docx import Document
from sqlalchemy import select


def make_docx(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    doc.save(buf)
    return buf.getvalue()


def test_import_duplicate_detection_and_publish_gate(client):
    payload = make_docx([
        "数学测试卷",
        "一、单选题（1题，7分/个）",
        "1. 1+1=?", "A.1", "B.2", "C.3", "D.4",
        "答案：B", "解析：正确答案为 A。",
    ])

    response = client.post(
        "/api/admin/imports/docx",
        data={"subject_code": "math"},
        files={"file": ("math.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "pending_review"
    assert job["blocking_warning_count"] == 1

    duplicate = client.post(
        "/api/admin/imports/docx",
        data={"subject_code": "math"},
        files={"file": ("math.docx", payload, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == job["id"]
    assert duplicate.json()["reused"] is True

    blocked = client.post(f"/api/admin/imports/{job['id']}/publish")
    assert blocked.status_code == 409

    review = client.get(f"/api/admin/imports/{job['id']}/review").json()
    warning_id = review["warnings"][0]["id"]
    question = review["draft"]["sections"][0]["questions"][0]
    question["standard_answer_json"] = {"value": "A"}

    edited = client.patch(
        f"/api/admin/imports/{job['id']}/review",
        json={
            "draft": review["draft"],
            "resolve_warning_ids": [warning_id],
            "resolution_note": "人工核对解析文字后修正答案",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["blocking_warning_count"] == 0

    published = client.post(f"/api/admin/imports/{job['id']}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["paper_id"] is not None

    paper = client.get(f"/api/papers/{published.json()['paper_id']}")
    assert paper.status_code == 200
    assert paper.json()["sections"][0]["questions"][0]["standard_answer_json"] == {"value": "A"}
