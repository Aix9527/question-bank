from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.services.imports.docx_parser import parse_docx
from app.services.imports.question_mapper import map_document

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"


def test_initial_manifest_has_two_papers_per_subject_and_exact_sources():
    manifest = json.loads((DATA / "import-manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"] == {"chinese": 2, "math": 2, "english": 2}
    assert len(manifest["papers"]) == 6
    for paper in manifest["papers"]:
        source = DATA / "source_papers" / paper["source_filename"]
        payload = source.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == paper["source_sha256"]
        assert len(payload) == paper["source_size"]


def test_initial_six_real_papers_map_to_expected_counts_scores_and_review_gate():
    manifest = json.loads((DATA / "import-manifest.json").read_text(encoding="utf-8"))
    decisions = json.loads((DATA / "initial-review-decisions.json").read_text(encoding="utf-8"))
    by_filename = {item["source_filename"]: item for item in decisions["papers"]}

    for paper in manifest["papers"]:
        source = DATA / "source_papers" / paper["source_filename"]
        draft = map_document(parse_docx(source), paper["subject_code"])
        questions = [q for section in draft["sections"] for q in section["questions"]]
        assert len(questions) == paper["expected_question_count"], paper["source_filename"]
        assert sum(q["score"] for q in questions) == paper["expected_total_score"], paper["source_filename"]
        assert draft["media_count"] == paper["expected_media_count"]
        for section in draft["sections"]:
            if paper["subject_code"] == "english" and "补全对话" in section["title"]:
                continue
            for question in section["questions"]:
                if question["type"] == "single_choice":
                    assert len(question["options"]) == 4, (paper["source_filename"], question["candidate_id"])

        blocking = [w for w in draft["warnings"] if w["severity"] == "blocking"]
        expected_blocking = paper["expected_blocking_warnings_before_review"]
        assert len(blocking) == expected_blocking, paper["source_filename"]
        if blocking:
            decision = by_filename[paper["source_filename"]]
            assert len(decision["corrections"]) == len(blocking)


def test_initial_review_decisions_write_canonical_value_field():
    decisions = json.loads((DATA / 'initial-review-decisions.json').read_text(encoding='utf-8'))
    for paper in decisions.get('papers', []):
        for correction in paper.get('corrections', []):
            assert correction['field'] == 'standard_answer_json.value'
