import Link from 'next/link';
import { apiGet } from '../../../lib/server-api';

type Paper = { id:number; title:string; paper_type:string; total_score:number|null; time_limit_minutes:number|null; version:number };
const names: Record<string,string> = { chinese:'语文', math:'数学', english:'英语' };

export default async function SubjectPage({ params }: { params: Promise<{subject:string}> }) {
  const { subject } = await params;
  const papers = await apiGet<Paper[]>(`/api/subjects/${subject}/papers`);
  return <main className="shell">
    <section className="hero"><h1>{names[subject] ?? subject}题库</h1><p>模拟考试、顺序练习、随机练习、错题复练将共用同一题库数据。</p></section>
    <div className="list">
      {papers.length === 0 && <div className="card"><strong>暂无已发布试卷</strong><p className="muted">首批 Word 模拟卷会经过导入审核后显示在这里。</p></div>}
      {papers.map(paper => <Link className="paper" href={`/papers/${paper.id}`} key={paper.id}>
        <span><strong>{paper.title}</strong><br/><small className="muted">版本 v{paper.version}</small></span><span>查看试卷 →</span>
      </Link>)}
    </div>
  </main>;
}
