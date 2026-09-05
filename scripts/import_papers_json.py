# -*- coding: utf-8 -*-
"""Import normalized paper JSON (schema_version 1) into Supabase/PostgreSQL.

Usage:
  set QUESTION_BANK_DATABASE_URL=postgresql://...
  python scripts/import_papers_json.py <file1.json> [file2.json ...] [--status published|draft] [--draft-below N]

Rules:
- Idempotent: skips papers whose papers.source_file marker already exists.
- subject_code from paper JSON (chinese/math/english).
- answer_mode: single_choice/multiple_choice -> exact; fill_blank -> normalized_text; else manual.
- standard_answer_json normalised: {"answer":X} -> {"value":X}; plain str -> {"value":str};
  reference-style dicts kept; missing -> NULL.
- --draft-below N: papers with fewer than N questions stored as draft regardless of --status.
"""
import argparse, json, os, sys, re
import psycopg2

SUBJECT = {"chinese": 1, "math": 2, "english": 3}
AUTO = {"single_choice", "multiple_choice", "fill_blank"}

def std_json(type_, std):
    if std in (None, ""):
        return None
    if isinstance(std, dict):
        if "value" in std or "reference_html" in std or "values" in std:
            return std
        if "answer" in std:
            v = std["answer"]
            if type_ == "multiple_choice":
                vals = v if isinstance(v, list) else ([x.strip() for x in str(v).split(",") if x.strip()] if v else [])
                return {"values": vals} if vals else None
            return {"value": str(v)}
        return std
    s = str(std).strip()
    if not s:
        return None
    return {"value": s} if type_ in AUTO else {"reference_html": s}

def mode_for(type_):
    if type_ in ("single_choice", "multiple_choice"):
        return "exact"
    if type_ == "fill_blank":
        return "normalized_text"
    return "manual"

def strip_stem(t):
    if not t:
        return ""
    return t.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--status", default="draft")
    ap.add_argument("--draft-below", type=int, default=0)
    args = ap.parse_args()
    url = os.environ.get("QUESTION_BANK_DATABASE_URL")
    if not url:
        print("NO_URL"); sys.exit(2)
    conn = psycopg2.connect(url, connect_timeout=20)
    conn.autocommit = False
    cur = conn.cursor()
    summary = []
    try:
        for path in args.files:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            base = os.path.basename(path).rsplit(".", 1)[0]
            papers = data.get("papers", data if isinstance(data, list) else [])
            if not isinstance(papers, list):
                papers = []
            for pi, paper in enumerate(papers, 1):
                subject_code = paper.get("subject_code") or ""
                subj_id = SUBJECT.get(subject_code)
                if not subj_id:
                    summary.append((base, pi, "SKIP", "unknown subject_code " + subject_code)); continue
                marker = "json:" + base + "#p" + str(pi)
                cur.execute("select id from papers where source_file=%s limit 1", (marker,))
                if cur.fetchone():
                    summary.append((base, pi, "SKIP", "already imported")); continue
                title = (paper.get("title") or "未命名试卷").strip()
                qcount = sum(len(s.get("questions") or []) for s in (paper.get("sections") or []))
                status = args.status
                if args.draft_below and qcount < args.draft_below:
                    status = "draft"
                total = paper.get("total_score")
                cur.execute("""insert into papers(subject_id,title,source_file,paper_type,total_score,time_limit_minutes,status,version)
                               values(%s,%s,%s,%s,%s,%s,%s,1) returning id""",
                            (subj_id, title, marker, paper.get("paper_type") or "mock",
                             total, paper.get("time_limit_minutes"), status))
                paper_id = cur.fetchone()[0]
                q_added = 0
                for oi, sec in enumerate(paper.get("sections") or [], 1):
                    qs = sec.get("questions") or []
                    sec_title = (sec.get("title") or f"第{oi}部分").strip()
                    sec_total = sec.get("score_total")
                    cur.execute("""insert into paper_sections(paper_id,title,order_index,instruction,score_total)
                                   values(%s,%s,%s,%s,%s) returning id""",
                                (paper_id, sec_title, oi, sec.get("instruction"), sec_total))
                    section_id = cur.fetchone()[0]
                    for qi, q in enumerate(qs, 1):
                        if not (q.get("stem_html") or "").strip():
                            continue
                        typ = q.get("type") or ("single_choice" if q.get("options") else "short_answer")
                        stem = strip_stem(q["stem_html"])
                        material = q.get("material_html") or None
                        score = float(q.get("score") or 0)
                        std = std_json(typ, q.get("standard_answer"))
                        cur.execute("""insert into questions(subject_id,type,stem_html,material_html,answer_mode,
                                       standard_answer_json,explanation_html,score,difficulty,knowledge_points,source,status,version)
                                       values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1) returning id""",
                                    (subj_id, typ, stem, material, mode_for(typ), json.dumps(std, ensure_ascii=False) if std is not None else None,
                                     q.get("explanation_html"), score, q.get("difficulty"), json.dumps(q.get("knowledge_points"), ensure_ascii=False) if q.get("knowledge_points") else None,
                                     paper.get("source", {}).get("url") if isinstance(paper.get("source"), dict) else None, status))
                        question_id = cur.fetchone()[0]
                        cur.execute("""insert into paper_questions(paper_id,question_id,section_id,order_index,score_override)
                                       values(%s,%s,%s,%s,NULL)""", (paper_id, question_id, section_id, qi))
                        for oi2, opt in enumerate(q.get("options") or [], 1):
                            label = opt.get("label") if isinstance(opt, dict) else chr(64 + oi2)
                            content = opt.get("content_html") if isinstance(opt, dict) else opt
                            if content is None:
                                content = ""
                            cur.execute("""insert into question_options(question_id,label,content_html,order_index)
                                           values(%s,%s,%s,%s)""", (question_id, label, content, oi2))
                        q_added += 1
                conn.commit()
                summary.append((base, pi, "OK", f"paper#{paper_id} '{title}' questions={q_added} status={status}"))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print("IMPORT_ERROR", exc)
        sys.exit(1)
    finally:
        cur.close(); conn.close()
    for row in summary:
        print(row[0], "p" + str(row[1]), row[2], row[3])
    print("DONE", len([s for s in summary if s[2] == "OK"]))

if __name__ == "__main__":
    main()
