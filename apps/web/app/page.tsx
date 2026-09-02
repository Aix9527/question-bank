import Link from 'next/link';
import { apiGet } from '../lib/server-api';
import LogoutButton from '../components/LogoutButton';

type Subject = { id:number; code:string; name:string; enabled:boolean };
type Stats={totals:{attempts:number;accuracy:number|null;wrong_questions:number;mastered_wrong_questions:number}};
type User={id:number;username:string;display_name:string|null;role:string};
const descriptions: Record<string,string> = {chinese:'阅读、文言文、基础知识、作文训练与主观题批复',math:'选择、填空、计算与解答题，支持自动判分与错题复练',english:'词汇语法、完形、阅读、翻译与写作训练'};

export default async function Home() {
  const [subjects,stats,user]=await Promise.all([apiGet<Subject[]>('/api/subjects'),apiGet<Stats>('/api/me/statistics'),apiGet<User>('/api/auth/me')]);
  const localMode=(process.env.QUESTION_BANK_AUTH_REQUIRED??'false').toLowerCase()!=='true'; const canAdmin=user.role==='admin'||localMode;
  return <main className="shell">
    <section className="hero"><div className="row"><div><div className="eyebrow">v0.5</div><h1>专科复习在线题库</h1><p>语文、数学、英语分别建立，做题记录按账号独立保存，可反复练习与批复。</p></div><div className="identityBox"><span>{user.display_name??user.username}</span><small>{canAdmin?'管理员 / 学习':'学习账号'}</small>{!localMode&&<LogoutButton/>}</div></div></section>
    <nav className="quickNav"><Link href="/wrong">错题本 <b>{stats.totals.wrong_questions}</b></Link><Link href="/favorites">收藏题</Link><Link href="/history">成绩历史</Link><Link href="/statistics">学习统计</Link>{canAdmin&&<><Link href="/admin">管理后台</Link><Link href="/admin/reviews">主观题批改</Link><Link href="/admin/imports">DOCX导入</Link></>}</nav>
    <section className="metricGrid compact"><div className="metric"><span>已提交练习</span><strong>{stats.totals.attempts}</strong></div><div className="metric"><span>客观题正确率</span><strong>{stats.totals.accuracy===null?'—':`${Math.round(stats.totals.accuracy*100)}%`}</strong></div><div className="metric"><span>已掌握错题</span><strong>{stats.totals.mastered_wrong_questions}</strong></div></section>
    <section className="grid">{subjects.map(subject => <article className="card" key={subject.code}><h2>{subject.name}题库</h2><p>{descriptions[subject.code]}</p><Link className="button" href={`/subjects/${subject.code}`}>进入题库</Link></article>)}</section>
  </main>;
}
