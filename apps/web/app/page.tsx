import Link from 'next/link';
import { apiGet } from '../lib/server-api';

type Subject = { id:number; code:string; name:string; enabled:boolean };
type Stats={totals:{attempts:number;accuracy:number|null;wrong_questions:number;mastered_wrong_questions:number}};
const descriptions: Record<string,string> = {
  chinese:'阅读、文言文、基础知识、作文训练与主观题批复',
  math:'选择、填空、计算与解答题，支持自动判分与错题复练',
  english:'词汇语法、完形、阅读、翻译与写作训练',
  ai_trainer:'国家职业技能等级五级至一级，覆盖数据标注、模型训练与智能系统运维',
  ai_engineer:'国家职业技术技能标准初级至高级，覆盖机器学习、深度学习与AI工程',
  miit_ai_app:'工信部人工智能应用方向初/中/高级，聚焦场景落地与生成式AI应用',
  huawei_ai:'华为 HCIA / HCIP / HCIE-AI 三级，覆盖昇腾、MindSpore 与模型开发部署',
  aliyun_llm:'阿里云大模型工程师 ACP，覆盖提示词、RAG、微调、多Agent与生产实践',
  baidu_dl:'百度飞桨深度学习工程师初/中/高级，覆盖框架、训练、优化与部署',
  ms_azure_ai:'Microsoft Azure AI 基础（AI-901）与工程师（AI-103）',
  aws_ai:'AWS Certified AI Practitioner，覆盖AI/ML基础、生成式AI与安全治理',
  x1_ai:'1+X 人工智能技术应用初/中/高级，覆盖数据、模型、部署与治理',
};

export default async function Home() {
  const [subjects,stats]=await Promise.all([apiGet<Subject[]>('/api/subjects'),apiGet<Stats>('/api/me/statistics')]);
  return <main className="shell">
    <section className="hero"><div className="row"><div><div className="eyebrow">v0.5</div><h1>人工智能认证在线题库</h1><p>按证书与等级分类，覆盖国家认可、厂家认可与其他类认证；做题记录按账号独立保存，可反复练习与批复。</p></div><div className="identityBox"><span>学习账号</span><small>访客</small></div></div></section>
    <nav className="quickNav"><Link href="/wrong">错题本 <b>{stats.totals.wrong_questions}</b></Link><Link href="/favorites">收藏题</Link><Link href="/history">成绩历史</Link><Link href="/statistics">学习统计</Link></nav>
    <section className="metricGrid compact"><div className="metric"><span>已提交练习</span><strong>{stats.totals.attempts}</strong></div><div className="metric"><span>客观题正确率</span><strong>{stats.totals.accuracy===null?'—':`${Math.round(stats.totals.accuracy*100)}%`}</strong></div><div className="metric"><span>已掌握错题</span><strong>{stats.totals.mastered_wrong_questions}</strong></div></section>
    <section className="grid">{subjects.map(subject => <article className="card" key={subject.code}><h2>{subject.name}题库</h2><p>{descriptions[subject.code] ?? '人工智能认证题库，按证书与等级分类'}</p><Link className="button" href={`/subjects/${subject.code}`}>进入题库</Link></article>)}</section>
  </main>;
}
