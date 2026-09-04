# -*- coding: utf-8 -*-
"""将本地题库的内容刷新（stem/options/material 保真修复）同步到生产 PostgreSQL。

使用方式（连接串只从环境变量读取，不要写入脚本或提交日志）：
  set QUESTION_BANK_DATABASE_URL=postgresql://user:pass@host:6543/db   # PowerShell 示例
  python scripts/sync_content_refresh_to_pg.py

参数：
  --db      本地 SQLite 路径（默认 ../question_bank.db）
  --plan    刷新计划 JSON（默认读取 data/refresh_plan.json；缺省自动跳过并只按行标志处理）

脚本只更新刷新计划中标记的题目：题干(stem)、选项(options)、材料(material)；
参考答案、解析、分数与题号均保持不变。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / 'question_bank.db'
DEFAULT_PLAN = Path(os.environ.get('REFRESH_PLAN_PATH', '')) if os.environ.get('REFRESH_PLAN_PATH') else REPO_ROOT / 'data' / 'refresh_plan.json'


def load_plan(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f'plan not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))['rows']


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=str(DEFAULT_DB))
    parser.add_argument('--plan', default=str(DEFAULT_PLAN))
    args = parser.parse_args()

    url = os.environ.get('QUESTION_BANK_DATABASE_URL')
    if not url:
        raise SystemExit('环境变量 QUESTION_BANK_DATABASE_URL 未设置。')
    sqlite = create_engine(f'sqlite:///{args.db}')
    pg = create_engine(url, pool_pre_ping=True)

    plan_rows = load_plan(Path(args.plan))
    upd_stem = 0
    upd_options = 0
    upd_material = 0
    ids = []
    with sqlite.connect() as sl, pg.begin() as pgc:
        for rec in plan_rows:
            if any(h in k for k in rec.get('kinds', []) for h in ('人工', '语义', '格式微差')):
                continue
            qid = rec['qid']
            ids.append(qid)
            local = sl.execute(text('select stem_html, material_html from questions where id=:q'), {'q': qid}).first()
            if local is None:
                continue
            if 'stem_to' in rec:
                pgc.execute(text('update questions set stem_html=:s where id=:q'), {'s': local[0], 'q': qid})
                upd_stem += 1
            if rec.get('options'):
                pgc.execute(text('delete from question_options where question_id=:q'), {'q': qid})
                for o in rec['options']:
                    local_o = sl.execute(
                        text('select label, content_html, order_index from question_options where question_id=:q and order_index=:i'),
                        {'q': qid, 'i': o['order_index']},
                    ).first()
                    if local_o is None:
                        continue
                    pgc.execute(
                        text('insert into question_options (question_id, label, content_html, order_index) values (:q,:l,:c,:i)'),
                        {'q': qid, 'l': local_o[0], 'c': local_o[1], 'i': local_o[2]},
                    )
                upd_options += 1
            if 'material_to' in rec:
                pgc.execute(text('update questions set material_html=:m where id=:q'), {'m': local[1], 'q': qid})
                upd_material += 1
        print(f'completed: {len(ids)} rows -> stems={upd_stem} options={upd_options} material={upd_material}')
        print(f'question ids: {ids}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
