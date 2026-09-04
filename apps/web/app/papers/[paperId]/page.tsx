import BackTop from '../../../components/BackTop';
import { apiGet } from '../../../lib/server-api';
import FavoriteButton from '../../../components/FavoriteButton';
import StartPaperButton from '../../../components/StartPaperButton';
import RichHtml from '../../../components/RichHtml';

type Option={id:number;label:string;content_html:string};
type Question={id:number;stem_html:string;material_html:string|null;score:number;type:string;knowledge_points:string[]|null;options:Option[]};
type Section={id:number;title:string;instruction:string|null;questions:Question[]};
type Paper={id:number;subject_id:number;title:string;time_limit_minutes:number|null;sections:Section[]};

export default async function PaperPage({ params }: {params:Promise<{paperId:string}>}) {
  const {paperId}=await params; const paper=await apiGet<Paper>(`/api/papers/${paperId}`);
  return <main className="shell"><BackTop href="/">← 返回首页</BackTop><section className="hero"><h1>{paper.title}</h1><p>{paper.time_limit_minutes ? `考试时长 ${paper.time_limit_minutes} 分钟` : '练习试卷'} · 可收藏重点题，提交作答后的错题会自动进入错题本。</p><StartPaperButton subjectId={paper.subject_id} paperId={paper.id}/></section>{paper.sections.map(section=><section className="card" key={section.id} style={{marginBottom:18}}><h2>{section.title}</h2>{section.instruction&&<p className="muted">{section.instruction}</p>}<div className="list">{section.questions.map((q,index)=><div className="questionBlock" key={q.id}><div className="row"><strong>{index+1}. <RichHtml html={q.stem_html}/></strong><FavoriteButton questionId={q.id}/></div>{q.material_html&&(index===0||section.questions[index-1].material_html!==q.material_html)?<div className="materialBox"><RichHtml html={q.material_html}/></div>:null}<div className="optionList">{q.options.map(o=><div key={o.id}>{o.label}. <RichHtml html={o.content_html}/></div>)}</div><small className="muted">{q.score} 分 {q.knowledge_points?.length?`· ${q.knowledge_points.join(' / ')}`:''}</small></div>)}</div></section>)}</main>;
}
