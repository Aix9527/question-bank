'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';

import RichHtml from './RichHtml';

type Option={id:number;label:string;content_html:string;order_index?:number};
type Question={id:number;type:string;stem_html:string;material_html:string|null;score:number;options:Option[]};
type SavedAnswer={question_id:number;answer_json:any;grading_status:string;final_score:number|null;is_correct:boolean|null};
type Attempt={id:number;status:string;score:number|null;max_score:number|null;answers:SavedAnswer[]};

export default function AttemptRunner({ initialAttempt, questions }: {initialAttempt:Attempt;questions:Question[]}){
  const initialMap=useMemo(()=>new Map(initialAttempt.answers.map(a=>[a.question_id,a.answer_json])),[initialAttempt.answers]);
  const [index,setIndex]=useState(0);
  const [answers,setAnswers]=useState<Map<number,any>>(initialMap);
  const [message,setMessage]=useState('');
  const [result,setResult]=useState<Attempt|null>(initialAttempt.status==='in_progress'?null:initialAttempt);
  const question=questions[index];
  const current=answers.get(question?.id)??{};

  function setCurrent(next:any){setAnswers(new Map(answers).set(question.id,next));}
  function hasAnswer(q:Question,payload:any){if(q.type==='multiple_choice') return Array.isArray(payload?.values)&&payload.values.length>0;return String(payload?.value??'').trim().length>0;}
  async function save(q:Question){
    const payload=answers.get(q.id)??{};
    if(!hasAnswer(q,payload)){setMessage('请先填写本题答案。');return false;}
    const response=await fetch(`/api/learner-proxy/attempts/${initialAttempt.id}/answers/${q.id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({answer_json:payload,time_spent_seconds:0})});
    if(!response.ok){setMessage('保存失败，请重试。');return false;}
    setMessage(`第 ${index+1} 题已保存。`);return true;
  }
  async function next(){if(await save(question)&&index<questions.length-1)setIndex(index+1);}
  async function previous(){if(index>0)setIndex(index-1);}
  async function submit(){
    if(hasAnswer(question,answers.get(question.id)??{})){const ok=await save(question);if(!ok)return;}
    const response=await fetch(`/api/learner-proxy/attempts/${initialAttempt.id}/submit`,{method:'POST'});
    if(!response.ok){setMessage('提交失败，请重试。');return;}
    const data=await response.json();setResult(data);setMessage('');
  }
  if(!question) return <div className="card">这份试卷暂无题目。</div>;
  if(result) return <div className="card resultCard"><div className="eyebrow">提交完成</div><h2>{result.score??0} / {result.max_score??0} 分</h2><p>{result.status==='submitted'?'客观题已评分，主观题正在等待批改。':'本次成绩已完成。'}</p><div className="quickNav"><Link href="/history">查看成绩历史</Link><Link href="/wrong">查看错题本</Link>{result.status==='submitted'&&<Link href="/admin/reviews">进入批改中心</Link>}</div></div>;

  return <div className="attemptLayout"><section className="card attemptMain"><div className="row"><div className="eyebrow">第 {index+1} / {questions.length} 题</div><strong>{question.score} 分</strong></div>{question.material_html&&<div className="materialBox"><RichHtml html={question.material_html}/></div>}<h2><RichHtml html={question.stem_html}/></h2>{question.type==='multiple_choice'?<div className="optionList">{question.options.map(o=><label className="choiceLine" key={o.id}><input type="checkbox" checked={(current.values??[]).includes(o.label)} onChange={e=>{const old:string[]=current.values??[];setCurrent({values:e.target.checked?[...old,o.label]:old.filter(x=>x!==o.label)})}}/><span>{o.label}. <RichHtml html={o.content_html}/></span></label>)}</div>:question.options.length?<div className="optionList">{question.options.map(o=><label className="choiceLine" key={o.id}><input type="radio" name={`q-${question.id}`} checked={current.value===o.label} onChange={()=>setCurrent({value:o.label})}/><span>{o.label}. <RichHtml html={o.content_html}/></span></label>)}</div>:<textarea className="textArea largeAnswer" rows={question.type==='essay'||question.type==='subjective'?10:3} value={current.value??''} onChange={e=>setCurrent({value:e.target.value})} placeholder="输入你的答案"/>}<div className="attemptActions"><button className="ghostButton" onClick={previous} disabled={index===0}>上一题</button>{index<questions.length-1?<button className="button nativeButton" onClick={next}>保存并下一题</button>:<button className="button nativeButton" onClick={submit}>保存并提交</button>}</div>{index<questions.length-1&&<button className="submitLink" onClick={submit}>提前提交本次作答</button>}{message&&<p className="statusText darkStatus">{message}</p>}</section><aside className="card answerCard"><h3>答题卡</h3><div className="numberGrid">{questions.map((q,i)=><button key={q.id} onClick={()=>setIndex(i)} className={`${i===index?'active ':''}${hasAnswer(q,answers.get(q.id)??{})?'answered':''}`}>{i+1}</button>)}</div><p className="muted">蓝色：当前题 · 深色：已填写。答案在切换到下一题时自动保存；刷新后可恢复已保存答案。</p></aside></div>;
}
