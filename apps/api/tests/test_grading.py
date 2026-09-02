from types import SimpleNamespace

import pytest

from app.services.grading import grade_answer


@pytest.mark.parametrize(
    'question,answer,expected_correct,expected_score',
    [
        (SimpleNamespace(type='single_choice', answer_mode='exact', standard_answer_json={'value': 'B'}, score=5), {'value': 'B'}, True, 5),
        (SimpleNamespace(type='single_choice', answer_mode='exact', standard_answer_json={'value': 'B'}, score=5), {'value': 'A'}, False, 0),
        (SimpleNamespace(type='multiple_choice', answer_mode='exact_only', standard_answer_json={'values': ['A', 'C']}, score=6), {'values': ['C', 'A']}, True, 6),
        (SimpleNamespace(type='fill_blank', answer_mode='normalized_text', standard_answer_json={'value': 'Hello World'}, score=4), {'value': '  hello   world '}, True, 4),
        (SimpleNamespace(type='fill_blank', answer_mode='numeric_tolerance', standard_answer_json={'value': 3.14, 'tolerance': 0.01}, score=4), {'value': '3.145'}, True, 4),
        (SimpleNamespace(type='fill_blank', answer_mode='multiple_acceptable', standard_answer_json={'values': ['colour', 'color']}, score=4), {'value': 'COLOR'}, True, 4),
    ],
)
def test_grade_answer_modes(question, answer, expected_correct, expected_score):
    result = grade_answer(question, answer)
    assert result.is_correct is expected_correct
    assert result.score == expected_score


def test_grade_answer_does_not_crash_on_non_object_payload():
    question = SimpleNamespace(type='single_choice', answer_mode='exact', standard_answer_json={'value': 'B'}, score=5)
    result = grade_answer(question, 'B')
    assert result.is_correct is False
    assert result.score == 0

@pytest.mark.parametrize(
    'answer_mode,standard,submitted,expected_score',
    [
        ('exact', {'answer': 'B'}, {'value': 'B'}, 5),
        ('normalized_text', {'answer': ' Hello World '}, {'value': 'hello   world'}, 5),
        ('numeric_exact', {'answer': '3.14'}, {'value': 3.14}, 5),
    ],
)
def test_grade_answer_accepts_legacy_answer_key_for_scalar_standard(answer_mode, standard, submitted, expected_score):
    question = SimpleNamespace(type='test', answer_mode=answer_mode, standard_answer_json=standard, score=expected_score)
    result = grade_answer(question, submitted)
    assert result.is_correct is True
    assert result.score == expected_score
