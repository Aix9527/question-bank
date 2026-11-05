import Link from 'next/link';
import { apiGet } from '../../../lib/server-api';

type Paper = { id:number; title:string; paper_type:string; total_score:number|null; time_limit_minutes:number|null; version:number };
type Subject = { id:number; code:string; name:string; enabled:boolean };

export default async function SubjectPage({ params }: { params: Promise<{subject:string}> }) {
  const { subject } = await params;
  const [papers, subjects] = await Promise.all([
    apiGet<Paper[]>(`/api/subjects/${subject}/papers`),
    apiGet<Subject[]>('/api/subjects'),
  ]);
  const subjectName = subjects.find(s => s.code === subject)?.name ?? subject;

  // 按“认可类型 · 等级”中的认可类型分组，实现 证书 → 认可类型 → 等级 的层级展示
  const groups = new Map<string, Paper[]>();
  for (const paper of papers) {
    const key = paper.title.includes(' · ') ? paper.title.split(' · ')[0] : '其他';
    groups.set(key, [...(groups.get(key) ?? []), paper]);
  }

  return <main className="shell">
    <section className="hero">
      <h1>{subjectName}题库</h1>
      <p>按认可类型与等级分类，模拟考试、顺序练习、随机练习、错题复练共用同一题库数据。</p>
    </section>
    {papers.length === 0 && <div className="card"><strong>暂无已发布试卷</strong><p className="muted">请稍后查看，或联系管理员。</p></div>}
    {[...groups.entries()].map(([recognition, items]) => (
      <section key={recognition}>
        <h2>{recognition}</h2>
        <div className="list">
          {items.map(paper => <Link className="paper" href={`/papers/${paper.id}`} key={paper.id}>
            <span>
              <strong>{paper.title}</strong><br/>
              <small className="muted">
                版本 v{paper.version}
                {paper.total_score ? ` · ${paper.total_score}分` : ''}
                {paper.time_limit_minutes ? ` · ${paper.time_limit_minutes}分钟` : ''}
              </small>
            </span>
            <span>查看试卷 →</span>
          </Link>)}
        </div>
      </section>
    ))}
  </main>;
}
