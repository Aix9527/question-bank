from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class GradeResult:
    is_correct: bool | None
    score: float | None
    requires_manual: bool = False


def _norm_text(value: Any) -> str:
    return " ".join(str(value).strip().casefold().split())


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def _object_payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _scalar_value(payload: dict[str, Any], default: Any = None) -> Any:
    """Read canonical scalar answer values with v0.3 legacy compatibility.

    New writes use ``value``. Existing imported data may contain ``answer``;
    keep that alias read-only so historical question records continue to grade.
    """
    if "value" in payload:
        return payload.get("value")
    if "answer" in payload:
        return payload.get("answer")
    return default


def grade_answer(question, answer_json) -> GradeResult:
    mode = question.answer_mode
    standard = _object_payload(question.standard_answer_json)
    answer = _object_payload(answer_json)
    score = float(question.score)

    if mode in {"manual", "subjective"}:
        return GradeResult(is_correct=None, score=None, requires_manual=True)

    if mode == "exact":
        correct = str(_scalar_value(answer)) == str(_scalar_value(standard))
        return GradeResult(correct, score if correct else 0.0)

    if mode == "exact_only":
        actual = sorted(str(v) for v in answer.get("values", []))
        expected = sorted(str(v) for v in standard.get("values", []))
        correct = actual == expected
        return GradeResult(correct, score if correct else 0.0)

    if mode == "partial":
        actual = set(str(v) for v in answer.get("values", []))
        expected = set(str(v) for v in standard.get("values", []))
        if not actual or not actual.issubset(expected):
            return GradeResult(False, 0.0)
        if actual == expected:
            return GradeResult(True, score)
        partial_score = score * (len(actual) / len(expected)) if expected else 0.0
        return GradeResult(False, partial_score)

    if mode == "exact_text":
        correct = str(_scalar_value(answer, "")).strip() == str(_scalar_value(standard, "")).strip()
        return GradeResult(correct, score if correct else 0.0)

    if mode == "normalized_text":
        correct = _norm_text(_scalar_value(answer, "")) == _norm_text(_scalar_value(standard, ""))
        return GradeResult(correct, score if correct else 0.0)

    if mode == "numeric_exact":
        actual = _decimal(_scalar_value(answer))
        expected = _decimal(_scalar_value(standard))
        correct = actual is not None and expected is not None and actual == expected
        return GradeResult(correct, score if correct else 0.0)

    if mode == "numeric_tolerance":
        actual = _decimal(_scalar_value(answer))
        expected = _decimal(_scalar_value(standard))
        tolerance = _decimal(standard.get("tolerance", 0))
        correct = (
            actual is not None
            and expected is not None
            and tolerance is not None
            and abs(actual - expected) <= tolerance
        )
        return GradeResult(correct, score if correct else 0.0)

    if mode == "multiple_acceptable":
        actual = _norm_text(_scalar_value(answer, ""))
        expected = {_norm_text(v) for v in standard.get("values", [])}
        correct = actual in expected
        return GradeResult(correct, score if correct else 0.0)

    return GradeResult(is_correct=None, score=None, requires_manual=True)
