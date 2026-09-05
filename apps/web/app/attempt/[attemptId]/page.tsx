import BackTop from '../../../components/BackTop';
import { apiGet } from '../../../lib/server-api';
import AttemptRunner from '../../../components/AttemptRunner';

type Attempt={id:number;paper_id:number|null;status:string;score:number|null;max_score:number|null;answers:any[]};
type Option={id:number;label:string;content_html:string};
type Question={id:number;type:string;stem_html:string;material_html:string|null;score:number;options:Option[]};
type Section={id:number;title:string;instruction:string|null;questions:Question[]};
type Paper={id:number;subject_id:number;title:string;sections:Section[]};
type Subject={id:number;code:string;name:string};
type PaperListItem={id:number;title:string;status:string};
export default async function AttemptPage({params}:{params:Promise<{attemptId:string}>}){
  const {attemptId}=await params;
  const attempt=await apiGet<Attempt>(`/api/attempts/${attemptId}`);
  if(attempt.paper_id===null)return <main className="shell"><BackTop href="/wrong">← 返回错题本</BackTop><div className="card">此答题会话不是整卷练习。</div></main>;
  const paper=await apiGet<Paper>(`/api/papers/${attempt.paper_id}`);
  const sections=paper.sections;
  let switchPapers:PaperListItem[]=[];
  try{
    const subjects=await apiGet<Subject[]>('/api/subjects');
    const subject=subjects.find(s=>s.id===paper.subject_id);
    if(subject)switchPapers=(await apiGet<PaperListItem[]>(`/api/subjects/${subject.code}/papers`)).filter(p=>p.status==='published');
  }catch{switchPapers=[];}
  return <main className="shell"><BackTop href={`/papers/${paper.id}`}>← 返回试卷</BackTop><AttemptRunner initialAttempt={attempt} sections={sections} paperTitle={paper.title} switchPapers={switchPapers}/></main>;
}
