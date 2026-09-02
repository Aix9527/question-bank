from app.services.knowledge_points import infer_knowledge_points


def test_chinese_taxonomy_uses_stem_and_section():
    assert infer_knowledge_points(
        'chinese', 'single_choice', '下列字的注音，全都正确的一项是', None, '一、单项选择题'
    ) == ['语文/基础知识/字音']
    assert infer_knowledge_points(
        'chinese', 'short_answer', '请赏析这句话。', '现代文材料', '二、现代文阅读'
    ) == ['语文/阅读/现代文', '语文/阅读/简答']
    assert infer_knowledge_points(
        'chinese', 'essay', '请写一篇不少于600字的文章', None, '四、写作（60分）'
    ) == ['语文/写作/作文']


def test_math_taxonomy_recognizes_core_domains():
    assert infer_knowledge_points('math', 'single_choice', '已知cosx=3/5，则sin2x=', None, '一、单选题') == ['数学/三角函数']
    assert infer_knowledge_points('math', 'single_choice', '集合A={a,b},集合B={b,c},则A∪B=', None, '一、单选题') == ['数学/集合']
    assert infer_knowledge_points('math', 'solution', '求直线与圆的交点坐标', None, '三、解答题') == ['数学/解析几何']


def test_english_taxonomy_prefers_section_and_specific_grammar():
    assert infer_knowledge_points('english', 'single_choice', 'This is the park ______ we visited last weekend.', None, '二、词汇与语法知识') == ['英语/语法/定语从句']
    assert infer_knowledge_points('english', 'single_choice', 'If it ______ tomorrow, we will cancel the picnic.', None, '二、词汇与语法知识') == ['英语/语法/条件状语从句']
    assert infer_knowledge_points('english', 'single_choice', 'Choose the best answer.', None, '四、阅读理解') == ['英语/阅读理解']
    assert infer_knowledge_points('english', 'essay', 'Write a letter.', None, '六、书面表达（20分）') == ['英语/写作']


def test_publisher_adds_inferred_knowledge_points_when_draft_has_none(client):
    import json
    from pathlib import Path
    from sqlalchemy import select
    from app.models.question_bank import PaperQuestion, Question
    from app.services.imports.publisher import create_import_job, publish_job

    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((root / 'data/import-manifest.json').read_text(encoding='utf-8'))
    source_meta = next(item for item in manifest['papers'] if item['subject_code'] == 'math')
    source = root / 'data/source_papers' / source_meta['source_filename']

    with client.app.state.session_factory() as session:
        job, _ = create_import_job(session, subject_code='math', filename=source.name, data=source.read_bytes())
        paper = publish_job(session, job)
        qids = list(session.scalars(select(PaperQuestion.question_id).where(PaperQuestion.paper_id == paper.id)).all())
        questions = list(session.scalars(select(Question).where(Question.id.in_(qids))).all())
        assert len(questions) == 18
        assert all(question.knowledge_points for question in questions)
        assert any('数学/三角函数' in question.knowledge_points for question in questions)
