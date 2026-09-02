'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';


export default function StartPaperButton({ subjectId, paperId }: { subjectId:number; paperId:number }) {
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const router=useRouter();
  async function start(){
    setBusy(true);setError('');
    const response=await fetch(`/api/learner-proxy/attempts`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject_id:subjectId,paper_id:paperId,mode:'practice'})});
    setBusy(false);
    if(!response.ok){setError('创建答题会话失败');return;}
    const data=await response.json();router.push(`/attempt/${data.id}`);
  }
  return <div><button className="button nativeButton" onClick={start} disabled={busy}>{busy?'正在创建…':'开始在线做题'}</button>{error&&<span className="errorText"> {error}</span>}</div>;
}
