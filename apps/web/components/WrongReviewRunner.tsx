'use client';

import { useMemo, useState } from 'react';

import RichHtml from './RichHtml';

type Option = { id:number; label:string; content_html:string; order_index:number };
type Question = { id:number; type:string; stem_html:string; material_html:string|null; score:number; options:Option[] };
type WrongItem = { question_id:number; question:Question };

export default function WrongReviewRunner({ items, subjectName }: { items: WrongItem[]; subjectName:string }) {
  const [attemptId, setAttemptId] = useState<number|null>(null);
  const [index, setIndex] = useState(0);
  const [value, setValue] = useState('');
  const [values, setValues] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [finished, setFinished] = useState(false);
  const question = items[index]?.question;
  const questionIds = useMemo(() => items.map(item => item.question_id), [items]);

  async function start() {
    setMessage('正在创建复练…');
    const response = await fetch(`/api/learner-proxy/me/wrong-questions/review-attempt`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question_ids:questionIds})
    });
    if (!response.ok) { setMessage('创建失败，请刷新后重试。'); return; }
    const data = await response.json();
    setAttemptId(data.attempt.id);
    setMessage('复练已开始，每题答案会立即保存。');
  }

  function payloadFor(q: Question) {
    if (q.type === 'multiple_choice') return { values };
    return { value };
  }

  async function saveAndNext() {
    if (!attemptId || !question) return;
    const response = await fetch(`/api/learner-proxy/attempts/${attemptId}/answers/${question.id}`, {
      method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({answer_json:payloadFor(question), time_spent_seconds:0})
    });
    if (!response.ok) { setMessage('答案保存失败。'); return; }
    setValue(''); setValues([]);
    if (index < items.length - 1) { setIndex(index + 1); setMessage(`第 ${index + 1} 题已保存。`); }
    else {
      const submitted = await fetch(`/api/learner-proxy/attempts/${attemptId}/submit`, {method:'POST'});
      if (!submitted.ok) { setMessage('答案已保存，但提交失败，请重试。'); return; }
      const result = await submitted.json();
      setFinished(true);
      setMessage(`复练完成：${result.score ?? 0} / ${result.max_score ?? 0} 分。刷新页面可查看最新掌握状态。`);
    }
  }

  if (!items.length) return null;
  if (!attemptId) return <div className="reviewRunner"><strong>{subjectName}待复练：{items.length} 题</strong><p className="muted">连续两次复练答对后自动标记为“已掌握”。</p><button className="button nativeButton" onClick={start}>开始本组复练</button>{message && <p className="statusText">{message}</p>}</div>;
  if (finished) return <div className="reviewRunner successBox"><strong>{subjectName}复练已完成</strong><p>{message}</p></div>;

  return <div className="reviewRunner">
    <div className="eyebrow">{subjectName} · 第 {index+1}/{items.length} 题</div>
    {question.material_html && <div className="materialBox"><RichHtml html={question.material_html}/></div>}
    <h3><RichHtml html={question.stem_html}/></h3>
    {question.type === 'multiple_choice' ? <div className="optionList">{question.options.map(option => <label key={option.id} className="choiceLine"><input type="checkbox" checked={values.includes(option.label)} onChange={e => setValues(e.target.checked ? [...values, option.label] : values.filter(v => v !== option.label))}/><span>{option.label}. <RichHtml html={option.content_html}/></span></label>)}</div>
      : question.options.length ? <div className="optionList">{question.options.map(option => <label key={option.id} className="choiceLine"><input type="radio" name={`q-${question.id}`} value={option.label} checked={value===option.label} onChange={e=>setValue(e.target.value)}/><span>{option.label}. <RichHtml html={option.content_html}/></span></label>)}</div>
      : <input className="textInput" value={value} onChange={e=>setValue(e.target.value)} placeholder="输入答案" />}
    <button className="button nativeButton" onClick={saveAndNext} disabled={question.type==='multiple_choice' ? values.length===0 : value.trim()===''}>{index === items.length-1 ? '保存并完成复练' : '保存并下一题'}</button>
    {message && <p className="statusText">{message}</p>}
  </div>;
}
