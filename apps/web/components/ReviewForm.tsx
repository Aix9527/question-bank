'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

type AISuggestion={suggested_score:number;confidence:string;comment:string;strengths:string[];improvements:string[];rubric:any[];version:number};

export default function ReviewForm({ answerId, maxScore, initialSuggestion }: { answerId:number; maxScore:number; initialSuggestion?:AISuggestion|null }) {
  const [suggested, setSuggested] = useState(initialSuggestion ? String(initialSuggestion.suggested_score) : '');
  const [finalScore, setFinalScore] = useState('');
  const [comment, setComment] = useState('');
  const [ai, setAi] = useState<AISuggestion|null>(initialSuggestion??null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const router = useRouter();

  async function requestAI(){setAiBusy(true);setError('');const response=await fetch(`/api/admin-proxy/reviews/${answerId}/ai-suggest`,{method:'POST'});setAiBusy(false);if(!response.ok){const data=await response.json().catch(()=>({detail:'AI 建议生成失败'}));setError(data.detail??'AI 建议生成失败');return;}const data=await response.json() as AISuggestion;setAi(data);setSuggested(String(data.suggested_score));}
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    const response = await fetch(`/api/admin-proxy/reviews/${answerId}`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
        suggested_score: suggested === '' ? null : Number(suggested),
        final_score: Number(finalScore), comment: comment || null, rubric_json: ai?.rubric ?? null
      })
    });
    setBusy(false);
    if (!response.ok) { const data = await response.json().catch(()=>({detail:'提交失败'})); setError(data.detail ?? '提交失败'); return; }
    router.refresh();
  }

  return <form className="reviewForm" onSubmit={submit}>
    <div className="row"><strong>AI 辅助建议</strong><button type="button" className="ghostButton" onClick={requestAI} disabled={aiBusy}>{aiBusy?'生成中…':ai?'重新生成':'生成 AI 建议'}</button></div>
    {ai&&<div className="aiSuggestion"><h4>建议 {ai.suggested_score} / {maxScore} · 置信度 {ai.confidence} · v{ai.version}</h4><p>{ai.comment}</p>{ai.strengths.length>0&&<><strong>优点</strong><ul>{ai.strengths.map((x,i)=><li key={i}>{x}</li>)}</ul></>}{ai.improvements.length>0&&<><strong>改进</strong><ul>{ai.improvements.map((x,i)=><li key={i}>{x}</li>)}</ul></>}<button type="button" className="ghostButton" onClick={()=>setComment(ai.comment)}>采用 AI 评语到批语</button></div>}
    <label>AI/参考建议分（可改）<input className="textInput" type="number" min="0" max={maxScore} step="0.5" value={suggested} onChange={e=>setSuggested(e.target.value)} /></label>
    <label>最终得分（0–{maxScore}，必须人工确认）<input className="textInput" required type="number" min="0" max={maxScore} step="0.5" value={finalScore} onChange={e=>setFinalScore(e.target.value)} /></label>
    <label>批语<textarea className="textArea" rows={4} value={comment} onChange={e=>setComment(e.target.value)} placeholder="填写得分理由、修改建议或作文批语" /></label>
    <button className="button nativeButton" disabled={busy}>{busy ? '提交中…' : '确认人工批复'}</button>
    {error && <p className="errorText">{error}</p>}
  </form>;
}
