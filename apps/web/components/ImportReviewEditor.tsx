'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

type Warning={id:string;code:string;message:string;severity:string;candidate_id:string|null;resolved:boolean;resolution_note:string|null};
type Review={id:number;status:string;review_revision:number;draft:Record<string,unknown>;warnings:Warning[];blocking_warning_count:number};

export default function ImportReviewEditor({review}:{review:Review}){
  const router=useRouter();
  const [draftText,setDraftText]=useState(JSON.stringify(review.draft,null,2));
  const [checked,setChecked]=useState<string[]>([]);
  const [note,setNote]=useState('人工审核已确认并修正');
  const [status,setStatus]=useState('');
  const [busy,setBusy]=useState(false);
  const summary=useMemo(()=>{
    const d=review.draft as any; const sections=Array.isArray(d.sections)?d.sections:[];
    return {sections:sections.length,questions:sections.reduce((n:number,s:any)=>n+(Array.isArray(s.questions)?s.questions.length:0),0),score:sections.reduce((n:number,s:any)=>n+Number(s.score_total??0),0)};
  },[review.draft]);

  async function save(){
    setBusy(true); setStatus('');
    try{
      const draft=JSON.parse(draftText);
      const response=await fetch(`/api/admin-proxy/imports/${review.id}/review`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({draft,resolve_warning_ids:checked,resolution_note:note})});
      const payload=await response.json(); if(!response.ok) throw new Error(payload.detail??`HTTP ${response.status}`);
      setStatus('审核草稿已保存。'); setChecked([]); router.refresh();
    }catch(error){setStatus(error instanceof Error?error.message:'保存失败');}finally{setBusy(false);}
  }
  async function publish(){
    setBusy(true); setStatus('');
    try{
      const response=await fetch(`/api/admin-proxy/imports/${review.id}/publish`,{method:'POST'});
      const payload=await response.json(); if(!response.ok) throw new Error(payload.detail??`HTTP ${response.status}`);
      setStatus(`已发布为试卷 #${payload.paper_id}`); router.refresh();
    }catch(error){setStatus(error instanceof Error?error.message:'发布失败');}finally{setBusy(false);}
  }

  return <>
    <section className="metricGrid compact"><div className="metric"><span>大题</span><strong>{summary.sections}</strong></div><div className="metric"><span>题目</span><strong>{summary.questions}</strong></div><div className="metric"><span>总分</span><strong>{summary.score}</strong></div></section>
    <section className="twoCol importReviewGrid">
      <div className="card"><h2>审核警告</h2>{review.warnings.length===0?<p className="muted">没有解析警告。</p>:review.warnings.map(w=><label className="warningRow" key={w.id}><input type="checkbox" disabled={w.resolved} checked={w.resolved||checked.includes(w.id)} onChange={e=>setChecked(current=>e.target.checked?[...current,w.id]:current.filter(id=>id!==w.id))}/><span><b>{w.code}</b> · {w.candidate_id??'全局'}<br/><span className="muted">{w.message}</span>{w.resolved&&<><br/><span className="badge mastered">已解决</span></>}</span></label>)}</div>
      <div className="card"><h2>发布门禁</h2><p>当前状态：<b>{review.status}</b></p><p>未解决阻塞：<b>{review.blocking_warning_count}</b></p><label>审核说明<input className="textInput" value={note} onChange={e=>setNote(e.target.value)}/></label><div className="row importActions"><button className="ghostButton" disabled={busy} onClick={save}>保存审核</button><button className="button nativeButton" disabled={busy||review.blocking_warning_count>0||review.status==='published'} onClick={publish}>发布入库</button></div>{status&&<p className="muted">{status}</p>}</div>
    </section>
    <section className="card"><h2>结构化草稿 JSON</h2><p className="muted">可修改题干、答案、解析、分值和选项。保存审核后才会写入导入任务。</p><textarea className="textArea importJson" value={draftText} onChange={e=>setDraftText(e.target.value)} spellCheck={false}/></section>
  </>;
}
