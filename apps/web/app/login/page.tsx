'use client';

import {FormEvent, useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';

export default function LoginPage(){
  const [username,setUsername]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false); const router=useRouter();
  async function submit(event:FormEvent){event.preventDefault();setBusy(true);setError('');const response=await fetch('/api/session/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})});setBusy(false);if(!response.ok){const data=await response.json().catch(()=>({detail:'登录失败'}));setError(data.detail??'登录失败');return;}router.push('/');router.refresh();}
  return <main className="shell loginShell"><section className="card loginCard"><div className="eyebrow">v0.5</div><h1>登录题库</h1><p className="muted">学习账号只能查看自己的答题数据；管理员账号可进入题库管理与批改中心。</p><form className="reviewForm" onSubmit={submit}><label>用户名<input className="textInput" required value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username"/></label><label>密码<input className="textInput" type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/></label><button className="button nativeButton" disabled={busy}>{busy?'登录中…':'登录'}</button>{error&&<p className="errorText">{error}</p>}</form><p style={{marginTop:16}} className="muted">还没有账号？<Link href="/register" style={{color:'#175cd3',fontWeight:600}}>创建账号</Link></p></section></main>;
}
