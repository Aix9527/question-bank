import Link from 'next/link';
import BackTop from '../../../components/BackTop';
import { apiGetAdmin } from '../../../lib/server-api';
import ImportUploadForm from '../../../components/ImportUploadForm';

type ImportJob={id:number;subject_code:string;source_filename:string;title:string;status:string;blocking_warning_count:number;warning_count:number;published_paper_id:number|null};
const subjectNames:Record<string,string>={chinese:'语文',math:'数学',english:'英语'};

export default async function ImportAdminPage(){
  const jobs=await apiGetAdmin<ImportJob[]>('/api/admin/imports');
  return <main className="shell">
    <BackTop href="/">← 返回首页</BackTop>
    <section className="hero"><div className="eyebrow">v0.4 · Admin</div><h1>DOCX 导入审核</h1><p>解析只生成草稿；存在阻塞警告时必须人工确认后才能发布。</p></section>
    <ImportUploadForm />
    <section className="list">{jobs.length===0?<div className="card"><p className="muted">还没有导入任务。</p></div>:jobs.map(job=><article className="paper" key={job.id}><div><b>{job.title}</b><div className="muted">{subjectNames[job.subject_code]??job.subject_code} · {job.source_filename}</div></div><div className="row"><span className={`badge ${job.status==='pending_review'?'pending':job.status==='published'?'mastered':''}`}>{job.status}</span>{job.blocking_warning_count>0&&<span className="badge pending">阻塞 {job.blocking_warning_count}</span>}<Link className="ghostButton" href={`/admin/imports/${job.id}`}>审核</Link></div></article>)}</section>
  </main>;
}
