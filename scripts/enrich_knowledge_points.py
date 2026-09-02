from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / 'apps' / 'api'
sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select  # noqa: E402
from app.db import build_engine, build_session_factory  # noqa: E402
from app.models.core import Subject  # noqa: E402
from app.models.question_bank import PaperQuestion, PaperSection, Question  # noqa: E402
from app.services.knowledge_points import infer_knowledge_points  # noqa: E402


def main() -> int:
    parser=argparse.ArgumentParser(description='Infer structured knowledge points for existing questions.')
    parser.add_argument('--apply', action='store_true', help='Persist inferred tags. Default is dry-run.')
    parser.add_argument('--overwrite', action='store_true', help='Replace existing manual tags as well.')
    args=parser.parse_args()
    engine=build_engine(); factory=build_session_factory(engine)
    result={'mode':'apply' if args.apply else 'dry-run','questions':0,'eligible':0,'changed':0,'already_tagged':0,'by_subject':{},'top_points':{}}
    points=Counter()
    with factory() as session:
        subjects={row.id:row.code for row in session.scalars(select(Subject)).all()}
        questions=list(session.scalars(select(Question).order_by(Question.id)).all())
        result['questions']=len(questions)
        for q in questions:
            code=subjects.get(q.subject_id)
            if not code: continue
            if q.knowledge_points and not args.overwrite:
                result['already_tagged']+=1
                for point in q.knowledge_points: points[point]+=1
                continue
            section_title=session.scalar(
                select(PaperSection.title)
                .join(PaperQuestion, PaperQuestion.section_id==PaperSection.id)
                .where(PaperQuestion.question_id==q.id)
                .limit(1)
            )
            inferred=infer_knowledge_points(code,q.type,q.stem_html,q.material_html,section_title)
            if not inferred: continue
            result['eligible']+=1; result['changed']+=1
            result['by_subject'][code]=result['by_subject'].get(code,0)+1
            for point in inferred: points[point]+=1
            if args.apply: q.knowledge_points=inferred
        if args.apply: session.commit()
        else: session.rollback()
    result['top_points']=dict(points.most_common(30))
    print(json.dumps(result,ensure_ascii=False,indent=2)); engine.dispose(); return 0
if __name__=='__main__': raise SystemExit(main())
