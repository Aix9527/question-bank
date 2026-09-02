from sqlalchemy import select


def _seed_paper(client):
    from app.models.core import Subject
    from app.models.question_bank import Paper, PaperQuestion, PaperSection, Question, QuestionOption

    with client.app.state.session_factory() as session:
        math = session.scalar(select(Subject).where(Subject.code == "math"))
        paper = Paper(subject_id=math.id, title="数学（文）模拟卷 1", paper_type="mock", status="published", version=1)
        session.add(paper)
        session.flush()
        section = PaperSection(paper_id=paper.id, title="一、选择题", order_index=1, instruction="每题5分", score_total=10)
        session.add(section)
        session.flush()
        q1 = Question(subject_id=math.id, type="single_choice", stem_html="1+1=?", answer_mode="exact", standard_answer_json={"value": "B"}, score=5, version=1, status="published")
        q2 = Question(subject_id=math.id, type="single_choice", stem_html="2+2=?", answer_mode="exact", standard_answer_json={"value": "C"}, score=5, version=1, status="published")
        session.add_all([q1, q2])
        session.flush()
        session.add_all([
            QuestionOption(question_id=q1.id, label="A", content_html="1", order_index=1),
            QuestionOption(question_id=q1.id, label="B", content_html="2", order_index=2),
            QuestionOption(question_id=q2.id, label="A", content_html="2", order_index=1),
            QuestionOption(question_id=q2.id, label="C", content_html="4", order_index=2),
        ])
        session.add_all([
            PaperQuestion(paper_id=paper.id, question_id=q1.id, section_id=section.id, order_index=1, score_override=5),
            PaperQuestion(paper_id=paper.id, question_id=q2.id, section_id=section.id, order_index=2, score_override=5),
        ])
        session.commit()
        return paper.id


def test_subject_papers_are_isolated_and_ordered(client):
    paper_id = _seed_paper(client)

    math_response = client.get('/api/subjects/math/papers')
    chinese_response = client.get('/api/subjects/chinese/papers')

    assert math_response.status_code == 200
    assert [p['id'] for p in math_response.json()] == [paper_id]
    assert chinese_response.status_code == 200
    assert chinese_response.json() == []


def test_paper_returns_sections_questions_and_ordered_options(client):
    paper_id = _seed_paper(client)

    response = client.get(f'/api/papers/{paper_id}')
    assert response.status_code == 200
    body = response.json()
    assert body['title'] == '数学（文）模拟卷 1'
    assert [s['title'] for s in body['sections']] == ['一、选择题']
    questions = body['sections'][0]['questions']
    assert [q['stem_html'] for q in questions] == ['1+1=?', '2+2=?']
    assert [o['label'] for o in questions[0]['options']] == ['A', 'B']
