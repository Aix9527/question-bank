import Link from 'next/link';
import { apiGet } from '../../../lib/server-api';
import AttemptRunner from '../../../components/AttemptRunner';

type Attempt={id:number;paper_id:number|null;status:string;score:number|null;max_score:number|null;answers:any[]};
type Question={id:number;type:string;stem_html:string;material_html:string|null;score:number;options:any[]};
type Paper={id:number;title:string;sections:{questions:Question[]}[]};
export default async function AttemptPage({params}:{params:Promise<{attemptId:string}>}){const {attemptId}=await params;const attempt=await apiGet<Attempt>(`/api/attempts/${attemptId}`);if(attempt.paper_id===null)return <main className="shell"><div className="card">此答题会话不是整卷练习。<br/><Link className="backLink" href="/wrong">返回错题本</Link></div></main>;const paper=await apiGet<Paper>(`/api/papers/${attempt.paper_id}`);const questions=paper.sections.flatMap(s=>s.questions);return <main className="shell"><section className="hero"><h1>{paper.title}</h1><p>答案逐题保存，刷新页面后会恢复已经保存的内容。</p></section><AttemptRunner initialAttempt={attempt} questions={questions}/><Link className="backLink" href={`/papers/${paper.id}`}>← 返回试卷</Link></main>}
