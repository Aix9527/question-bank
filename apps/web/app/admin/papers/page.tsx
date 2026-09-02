import Link from 'next/link';
import {apiGetAdmin} from '../../../lib/server-api';
import AdminPaperCreateForm from '../../../components/AdminPaperCreateForm';
import AdminPaperRow from '../../../components/AdminPaperRow';
type Paper={id:number;title:string;subject_code:string;paper_type:string;total_score:number|null;time_limit_minutes:number|null;status:string;version:number;section_count:number;question_count:number};
export default async function AdminPapersPage(){const papers=await apiGetAdmin<Paper[]>('/api/admin/papers');return <main className="shell"><section className="hero"><h1>试卷管理</h1><p>已发布试卷不会物理删除；删除动作统一进入 archived。</p></section><AdminPaperCreateForm/><section className="list">{papers.map(p=><AdminPaperRow key={p.id} paper={p}/>)}</section><Link className="backLink" href="/admin">← 返回管理后台</Link></main>}
