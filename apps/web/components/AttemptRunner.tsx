'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import RichHtml from './RichHtml';

type Option={id:number;label:string;content_html:string;order_index?:number};
type Question={id:number;type:string;stem_html:string;material_html:string|null;score:number;options:Option[]};
type Section={id:number;title:string;instruction:string|null;questions:Question[]};
type SavedAnswer={question_id:number;answer_json:any;grading_status:string;final_score:number|null;is_correct:boolean|null};
type Attempt={id:number;paper_id?:number|null;status:string;score:number|null;max_score:number|null;answers:SavedAnswer[]};
type PaperSwitch={id:number;title:string};

export default function AttemptRunner({initialAttempt,sections,paperTitle,switchPapers}:{initialAttempt:Attempt;sections:Section[];paperTitle:string;switchPapers:PaperSwitch[]}){
  const router=useRouter();
  const initialMap=useMemo(()=>new Map(initialAttempt.answers.map(a=>[a.question_id,a.answer_json])),[initialAttempt.answers]);
  const [secIndex,setSecIndex]=useState(0);
  const [answers,setAnswers]=useState<Map<number,any>>(initialMap);
  const [message,setMessage]=useState('');
  const [result,setResult]=useState<Attempt|null>(initialAttempt.status==='in_progress'?null:initialAttempt);
  const [statsOpen,setStatsOpen]=useState(false);
  const [switchOpen,setSwitchOpen]=useState(false);
  const section=sections[secIndex]??sections[0];

  const starts=useMemo(()=>{const arr:number[]=[];let acc=1;sections.forEach(s=>{arr.push(acc);acc+=s.questions.length;});return arr;},[sections]);
  const totalQuestions=useMemo(()=>sections.reduce((n,s)=>n+s.questions.length,0),[sections]);
  const answeredCount=useMemo(()=>questionsOf(sections).filter(q=>hasAnswer(q,answers.get(q.id)??{})).length,[answers,sections]);
  function questionsOf(sectionsArr:Section[]){return sectionsArr.flatMap(s=>s.questions);}
  function ordinal(q:Question){return starts[secIndex]+section.questions.findIndex(x=>x.id===q.id);}
  function currentOf(q:Question){return answers.get(q.id)??{};}
  function setCurrent(q:Question,next:any){setAnswers(new Map(answers).set(q.id,next));}
  function hasAnswer(q:Question,payload:any){if(q.type==='multiple_choice')return Array.isArray(payload?.values)&&payload.values.length>0;return String(payload?.value??'').trim().length>0;}
  async function save(q:Question):Promise<boolean>{
    const payload=answers.get(q.id)??{};
    if(!hasAnswer(q,payload))return true;
    const response=await fetch(`/api/learner-proxy/attempts/${initialAttempt.id}/answers/${q.id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({answer_json:payload,time_spent_seconds:0})});
    if(!response.ok){setMessage('第 '+(ordinal(q))+' 题保存失败，请重试。');return false;}
    return true;
  }
  async function flushSection():Promise<boolean>{
    let saved=0;
    for(const q of section.questions){if(await save(q)){if(hasAnswer(q,answers.get(q.id)??{}))saved++;}else return false;}
    setMessage(`本大题已保存 ${saved} 题答案。`);
    return true;
  }
  async function goSection(i:number){if(i===secIndex)return;const ok=await flushSection();if(ok){setSecIndex(i);window.scrollTo({top:0,behavior:'smooth'});setMessage('');}}
  async function submit(){
    if(!(await flushSection()))return;
    const response=await fetch(`/api/learner-proxy/attempts/${initialAttempt.id}/submit`,{method:'POST'});
    if(!response.ok){setMessage('提交失败，请重试。');return;}
    const data=await response.json();setResult(data);setMessage('');setStatsOpen(false);
  }
  function sectionScore(s:Section):{earned:number;total:number;pending:number}{
    const rows=result?.answers??[];
    let earned=0,total=0,pending=0;
    s.questions.forEach(q=>{total+=q.score||0;const a=rows.find(r=>r.question_id===q.id);if(!a){pending++;return;}if(typeof a.final_score==='number')earned+=a.final_score;else pending++;});
    return {earned,total,pending};
  }
  function renderQuestion(q:Question,idx:number){
    const current=currentOf(q);
    const controls=q.type==='multiple_choice'?<div className="optionList">{q.options.map(o=><label className="choiceLine" key={o.id}><input type="checkbox" checked={(current.values??[]).includes(o.label)} onChange={e=>{const old:string[]=current.values??[];setCurrent(q,{values:e.target.checked?[...old,o.label]:old.filter(x=>x!==o.label)})}}/><span>{o.label}. <RichHtml html={o.content_html}/></span></label>)}</div>:q.options.length?<div className="optionList">{q.options.map(o=><label className="choiceLine" key={o.id}><input type="radio" name={`q-${q.id}`} checked={current.value===o.label} onChange={()=>setCurrent(q,{value:o.label})}/><span>{o.label}. <RichHtml html={o.content_html}/></span></label>)}</div>:<textarea className="textArea largeAnswer" rows={q.type==='essay'||q.type==='subjective'?10:3} value={current.value??''} onChange={e=>setCurrent(q,{value:e.target.value})} placeholder="输入你的答案"/>;
    return <div className="questionBlock" key={q.id}><div className="row"><strong>{idx}. <RichHtml html={q.stem_html}/></strong><span className="muted">{q.score} 分</span></div>{q.material_html&&<div className="materialBox"><RichHtml html={q.material_html}/></div>}{controls}<p className="muted">{hasAnswer(q,current)?'已作答，答案随切换自动保存。':'未作答'}</p></div>;
  }

  if(!sections.length)return <div className="card">这份试卷暂无题目。</div>;
  if(result)return <div className="card resultCard" style={{maxWidth:640,margin:'0 auto'}}><div className="eyebrow">提交完成</div><h1 style={{fontSize:22,margin:'14px 0 2px'}}>本次模拟考试得分</h1><h2 style={{fontSize:44,margin:'10px 0 4px'}}>{result.score??0}<span style={{fontSize:20,color:'var(--muted,#888)'}}> / {result.max_score??0} 分</span></h2><p className="muted">{result.status==='submitted'?'客观题已自动评分，主观题进入批改中心后计入总分。':'本次成绩已完成。'}</p><div style={{margin:'18px 0'}}>{sections.map(s=>{const r=sectionScore(s);return <div className="row" key={s.id} style={{justifyContent:'space-between',padding:'7px 0',borderBottom:'1px dashed #eee'}}><span>{s.title}</span><span>{r.pending?(r.earned>0?`${r.earned} 分`:'待批改'):`${r.earned} / ${r.total} 分`}</span></div>;})}</div><div className="quickNav"><Link href="/history">查看成绩历史</Link><Link href="/wrong">查看错题本</Link>{result.status==='submitted'&&<Link href="/admin/reviews">进入批改中心</Link>}</div></div>;

  return <><div className="awbar"><div className="awbarTitle"><span className="eyebrow" style={{margin:0}}>{paperTitle}</span><strong>第 {secIndex+1} / {sections.length} 大题 · {section.title}</strong></div><div className="awbarBtns">
    <div className="awMenuWrap"><button className="ghostButton" onClick={()=>{setSwitchOpen(!switchOpen);setStatsOpen(false);}}>切换下一套试卷 ▾</button>{switchOpen&&<div className="awMenu">{switchPapers.filter(p=>p.id!==initialAttempt.paper_id).map(p=><button key={p.id} className="awMenuItem" onClick={()=>router.push(`/papers/${p.id}`)}>{p.title}</button>)}{switchPapers.length<=1&&<span className="muted" style={{padding:8}}>暂无其他试卷</span>}</div>}</div>
    <button className="ghostButton" onClick={()=>{setStatsOpen(!statsOpen);setSwitchOpen(false);}}>统计得分</button>
    <button className="button nativeButton" onClick={submit}>提交试卷</button>
  </div></div>
  {statsOpen&&<div className="awStats"><div className="row" style={{justifyContent:'space-between'}}><strong>已作答 {answeredCount} / {totalQuestions}</strong></div>{sections.map((s,i)=><div className="row" key={s.id} style={{justifyContent:'space-between',fontSize:13}}><span>{i+1}. {s.title}</span><span>{s.questions.filter(q=>hasAnswer(q,answers.get(q.id)??{})).length} / {s.questions.length} 题</span></div>)}<p className="muted" style={{marginBottom:0}}>得分统计不含正确率；主观题按每题得分累加。</p></div>}
  <section className="card awSection" style={{marginTop:10}}><div className="row" style={{justifyContent:'space-between',alignItems:'baseline'}}><h2 style={{margin:0}}>{section.title}</h2><span className="muted">第 {starts[secIndex]}–{starts[secIndex]+section.questions.length-1} 题 · 共 {section.questions.length} 题</span></div>{section.instruction&&<p className="muted">{section.instruction}</p>}<div className="list" style={{marginTop:12}}>{section.questions.map((q,i)=>renderQuestion(q,starts[secIndex]+i))}</div></section>
  <div className="awNav"><button className="ghostButton" disabled={secIndex===0} onClick={()=>goSection(secIndex-1)}>上一大题</button><div className="awNavCenter"><button className="ghostButton" onClick={()=>{setStatsOpen(!statsOpen);}}>统计得分</button></div>{secIndex<sections.length-1?<button className="button nativeButton" onClick={()=>goSection(secIndex+1)}>保存本大题并进入下一大题</button>:<button className="button nativeButton" onClick={submit}>保存并提交试卷</button>}</div>
  {message&&<p className="statusText darkStatus">{message}</p>}
  <aside className="card awCard"><h3>答题卡</h3>{sections.map((s,i)=><div key={s.id} style={{marginBottom:10}}><p className="muted" style={{margin:'2px 0 6px'}}>{i+1}. {s.title}</p><div className="numberGrid">{s.questions.map((q,qi)=>{const globalIdx=starts[i]+qi;return <button key={q.id} onClick={()=>goSection(i)} className={`${i===secIndex?'active ':''}${hasAnswer(q,answers.get(q.id)??{})?'answered':''}`}>{globalIdx}</button>;})}</div></div>)}<p className="muted" style={{marginBottom:0}}>深色：已填写。每大题作答后点击"保存并进入下一大题"即可持久保存；刷新页面可恢复。</p></aside>
  <style>{`.awbar{position:sticky;top:0;z-index:30;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px;border-radius:12px;background:rgba(255,255,255,.92);box-shadow:0 2px 10px rgba(0,0,0,.08);margin-bottom:4px}.awbarTitle{display:flex;flex-direction:column;gap:2px}.awbarBtns{display:flex;gap:8px;flex-wrap:wrap;position:relative}.awMenuWrap{position:relative}.awMenu{position:absolute;right:0;top:calc(100% + 6px);min-width:230px;background:#fff;border:1px solid #e6e6e6;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:40;padding:6px;display:flex;flex-direction:column}.awMenuItem{padding:9px 10px;border-radius:8px;text-align:left;background:none;border:none;cursor:pointer;font-size:14px}.awMenuItem:hover{background:#f2f2f5}.awStats{background:#fff;border:1px solid #eee;border-radius:12px;padding:12px 14px;margin:8px 0;display:flex;flex-direction:column;gap:6px;box-shadow:0 2px 8px rgba(0,0,0,.05)}.awSection{padding:18px}.awNav{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin:12px 0}.awNavCenter{display:flex;gap:8px}.awCard{margin:12px 0}.awCard .numberGrid{margin-top:4px}@media(max-width:640px){.awbar{flex-direction:column;align-items:stretch}.awbarBtns{justify-content:center}}`}</style></>;
}
