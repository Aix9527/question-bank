from __future__ import annotations

from app.services.imports.question_mapper import map_document


def ast(lines: list[str], title: str = "测试卷") -> dict:
    return {
        "source_filename": f"{title}.docx",
        "source_sha256": "a" * 64,
        "source_size": 123,
        "media_count": 0,
        "blocks": [
            {"kind": "paragraph", "index": i, "style": "Normal", "text": line, "html": line, "rows": None}
            for i, line in enumerate(lines)
        ],
    }


def test_math_mapper_builds_choice_fill_and_manual_sections():
    from app.services.imports.question_mapper import map_document

    draft = map_document(
        ast([
            "2025年数学模拟题",
            "一、单选题（1题，7分/个）",
            "1. 1+1等于（ ）",
            "A.1", "B.2", "C.3", "D.4",
            "答案：B", "解析：基础计算",
            "二、填空题（1题，7分/个）",
            "1. 2+2=______",
            "答案：4",
            "三、解答题（1题，12分）",
            "1. 写出计算过程。",
            "答案：",
        ]),
        "math",
    )

    assert [s["title"] for s in draft["sections"]] == ["一、单选题（1题，7分/个）", "二、填空题（1题，7分/个）", "三、解答题（1题，12分）"]
    qs = [q for s in draft["sections"] for q in s["questions"]]
    assert [q["type"] for q in qs] == ["single_choice", "fill_blank", "solution"]
    assert qs[0]["standard_answer_json"] == {"value": "B"}
    assert qs[1]["standard_answer_json"] == {"value": "4"}
    assert qs[2]["answer_mode"] == "manual"


def test_english_mapper_flags_answer_explanation_conflict_as_blocking():
    from app.services.imports.question_mapper import map_document

    draft = map_document(
        ast([
            "考前模拟题二",
            "一、语音知识（1小题，每题2分，共2分）",
            "1.", "A. put", "B. but", "C. cut", "D. cup",
            "答案：B",
            "解析：A 中发音不同，故选 A。",
        ]),
        "english",
    )

    assert len(draft["sections"][0]["questions"]) == 1
    conflicts = [w for w in draft["warnings"] if w["code"] == "answer_explanation_conflict"]
    assert len(conflicts) == 1
    assert conflicts[0]["severity"] == "blocking"
    assert conflicts[0]["resolved"] is False


def _p(index: int, text: str) -> dict:
    return {"kind": "paragraph", "index": index, "style": "Normal", "text": text, "html": text, "rows": None, "equation_text": None, "unsupported_object_count": 0}


def test_english_mapper_recovers_questions_glued_to_explanation_and_unnumbered_next_stem():
    ast = {
        "source_filename": "english.docx", "source_sha256": "a" * 64, "source_size": 1,
        "media_count": 0, "unsupported_object_count": 0,
        "blocks": [
            _p(0, "考前模拟题"),
            _p(1, "二、词汇与语法知识（3小题，每题2分，共6分）"),
            _p(2, "6.First question?"), _p(3, "A. one"), _p(4, "B. two"), _p(5, "C. three"), _p(6, "D. four"),
            _p(7, "答案：D"), _p(8, "解析：because D。7.Second question?"),
            _p(9, "A. one"), _p(10, "B. two"), _p(11, "C. three"), _p(12, "D. four"),
            _p(13, "答案：A"), _p(14, "解析：because A。"),
            _p(15, "— Where did you go?"), _p(16, "— Home."),
            _p(17, "A. When"), _p(18, "B. Where"), _p(19, "C. Why"), _p(20, "D. How"),
            _p(21, "答案：B"), _p(22, "解析：because B。"),
        ],
    }
    draft = map_document(ast, "english")
    questions = draft["sections"][0]["questions"]
    assert len(questions) == 3
    assert [q["standard_answer_json"]["value"] for q in questions] == ["D", "A", "B"]
    assert "Second question" in questions[1]["stem_html"]
    assert "Where did you go" in questions[2]["stem_html"]


def test_english_reading_mapper_recovers_unlabeled_four_choice_group():
    ast = {
        "source_filename": "english.docx", "source_sha256": "b" * 64, "source_size": 1,
        "media_count": 0, "unsupported_object_count": 0,
        "blocks": [
            _p(0, "考前模拟题"),
            _p(1, "四、阅读理解（1小题，每题3分，共3分）"),
            _p(2, "Passage B"), _p(3, "Reading is useful."),
            _p(4, "What is the main idea?"),
            _p(5, "Reading is bad."), _p(6, "Reading has many benefits."), _p(7, "Reading is difficult."), _p(8, "Reading is expensive."),
            _p(9, "答案：B"), _p(10, "解析：故选 B。"),
        ],
    }
    draft = map_document(ast, "english")
    q = draft["sections"][0]["questions"][0]
    assert [o["label"] for o in q["options"]] == ["A", "B", "C", "D"]
    assert "Passage B" in (q["material_html"] or "")
    assert "main idea" in q["stem_html"]
    assert not [w for w in draft["warnings"] if w["code"] == "missing_options"]


def test_chinese_modern_subsection_instruction_is_not_counted_as_question():
    ast = {
        "source_filename": "chinese.docx", "source_sha256": "c" * 64, "source_size": 1,
        "media_count": 0, "unsupported_object_count": 0,
        "blocks": [
            _p(0, "语文模拟卷"),
            _p(1, "二、现代文阅读"),
            _p(2, "2、阅读文章，回答下列问题。（第1、2、3题各6分，第4题7分，共25分）"),
            _p(3, "文章正文"),
            _p(4, "1.问题一"), _p(5, "【参考答案】答一"),
            _p(6, "2.问题二"), _p(7, "【参考答案】答二"),
            _p(8, "3.问题三"), _p(9, "【参考答案】答三"),
            _p(10, "4.问题四"), _p(11, "【参考答案】答四"),
        ],
    }
    draft = map_document(ast, "chinese")
    questions = draft["sections"][0]["questions"]
    assert len(questions) == 4
    assert [q["score"] for q in questions] == [6.0, 6.0, 6.0, 7.0]
    assert sum(q["score"] for q in questions) == 25.0


def test_english_cloze_recovers_numbered_a_option_line():
    ast = {
        "source_filename":"english.docx","source_sha256":"d"*64,"source_size":1,"media_count":0,"unsupported_object_count":0,
        "blocks":[
            _p(0,"考前模拟题"), _p(1,"三、完形填空（1小题，每题2分，共2分）"),
            _p(2,"Passage with _21_."), _p(3,"21.A. worked"), _p(4,"B. studied"), _p(5,"C. rested"), _p(6,"D. unemployed"),
            _p(7,"答案：D"), _p(8,"解析：故选 D。"),
        ],
    }
    q=map_document(ast,"english")["sections"][0]["questions"][0]
    assert [o["label"] for o in q["options"]]==["A","B","C","D"]
    assert "worked" in q["options"][0]["content_html"]


def test_english_reading_material_sentence_starting_with_a_is_not_option():
    ast={
        "source_filename":"english.docx","source_sha256":"e"*64,"source_size":1,"media_count":0,"unsupported_object_count":0,
        "blocks":[
            _p(0,"考前模拟题"), _p(1,"四、阅读理解（1小题，每题3分，共3分）"),
            _p(2,"Passage C"), _p(3,"A new study has shown exercise helps."), _p(4,"More material."),
            _p(5,"What did the study show?"), _p(6,"Exercise is bad."), _p(7,"Exercise is good."), _p(8,"No effect."), _p(9,"More stress."),
            _p(10,"答案：B"), _p(11,"解析：故选 B。"),
        ],
    }
    q=map_document(ast,"english")["sections"][0]["questions"][0]
    assert [o["label"] for o in q["options"]]==["A","B","C","D"]
    assert "A new study" in (q["material_html"] or "")
    assert "A new study" not in q["options"][0]["content_html"]
