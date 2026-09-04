import BackTop from '../../components/BackTop';
import { apiGet } from '../../lib/server-api';
import WrongReviewRunner from '../../components/WrongReviewRunner';
import RichHtml from '../../components/RichHtml';

type Option={id:number;label:string;content_html:string;order_index:number};
type Question={id:number;subject_id:number;type:string;stem_html:string;material_html:string|null;score:number;knowledge_points:string[]|null;options:Option[]};
type Wrong={id:number;question_id:number;state:string;wrong_count:number;review_count:number;correct_review_count:number;consecutive_correct_count:number;question:Question};
type Subject={id:number;code:string;name:string};

export default async function WrongPage(){
  const [items, subjects]=await Promise.all([apiGet<Wrong[]>('/api/me/wrong-questions'),apiGet<Subject[]>('/api/subjects')]);
  const names=new Map(subjects.map(s=>[s.id,s.name]));
  const pending=items.filter(item=>item.state!=='mastered');
  const groups=new Map<number,Wrong[]>();
  for(const item of pending) groups.set(item.question.subject_id,[...(groups.get(item.question.subject_id)??[]),item]);
  return <main className="shell"><BackTop href="/">← 返回首页</BackTop><Top title="错题本" subtitle="答错自动收录；错题复练连续两次正确后进入已掌握。"/>
    {[...groups.entries()].map(([subjectId,group])=><WrongReviewRunner key={subjectId} items={group} subjectName={names.get(subjectId)??'题库'} />)}
    <div className="list">{items.length===0&&<div className="card"><strong>还没有错题</strong><p className="muted">提交客观题后，答错的题目会自动出现在这里。</p></div>}
      {items.map(item=><article className="card" key={item.id}><div className="row"><strong>{names.get(item.question.subject_id)} · {item.state==='mastered'?'已掌握':item.state==='learning'?'学习中':'待复习'}</strong><span className={`badge ${item.state}`}>{item.wrong_count} 次错误</span></div><h3><RichHtml html={item.question.stem_html}/></h3><p className="muted">复练 {item.review_count} 次 · 连续答对 {item.consecutive_correct_count} 次 {item.question.knowledge_points?.length ? `· ${item.question.knowledge_points.join(' / ')}`:''}</p></article>)}
    </div></main>;
}
function Top({title,subtitle}:{title:string;subtitle:string}){return <section className="hero"><h1>{title}</h1><p>{subtitle}</p></section>}
