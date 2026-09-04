'use client';

import {FormEvent, useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';

export default function RegisterPage(){
  const [username,setUsername]=useState(''); const [displayName,setDisplayName]=useState('');
  const [password,setPassword]=useState(''); const [confirm,setConfirm]=useState('');
  const [error,setError]=useState(''); const [busy,setBusy]=useState(false); const router=useRouter();
  async function submit(event:FormEvent){event.preventDefault();setBusy(true);setError('');
    if(password!==confirm){setError('两次输入的密码不一致');setBusy(false);return;}
    const response=await fetch('/api/session/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password,display_name:displayName||null})});
    setBusy(false);if(!response.ok){const data=await response.json().catch(()=>({detail:'注册失败'}));setError(data.detail??'注册失败');return;}
    router.push('/');router.refresh();}
  return <main className="shell loginShell"><section className="card loginCard"><div className="eyebrow">v0.5</div><h1>创建账号</h1><p className="muted">自助注册的学习账号可立即登录，与管理员创建的账号权限一致（仅学习权限）。</p><form className="reviewForm" onSubmit={submit}><label>用户名<input className="textInput" required value={username} onChange={e=>setUsername(e.target.value)} placeholder="字母/数字/._-，登录时使用" autoComplete="username"/></label><label>显示名称（选填）<input className="textInput" value={displayName} onChange={e=>setDisplayName(e.target.value)} maxLength={128} autoComplete="nickname"/></label><label>密码<input className="textInput" type="password" required minLength={1} value={password} onChange={e=>setPassword(e.target.value)} autoComplete="new-password"/></label><label>确认密码<input className="textInput" type="password" required value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="new-password"/></label><button className="button nativeButton" disabled={busy}>{busy?'注册中…':'创建账号'}</button>{error&&<p className="errorText">{error}</p>}</form><p style={{marginTop:14}} className="muted">已有账号？<Link href="/login" style={{color:'#175cd3'}}>返回登录</Link></p></section></main>;
}
