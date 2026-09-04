'use client';

import {FormEvent, useState} from 'react';
import {useRouter} from 'next/navigation';

export default function PasswordChangeForm(){
  const [oldPassword,setOldPassword]=useState(''); const [newPassword,setNewPassword]=useState('');
  const [confirm,setConfirm]=useState(''); const [message,setMessage]=useState(''); const [error,setError]=useState(''); const [busy,setBusy]=useState(false);
  const router=useRouter();
  async function submit(event:FormEvent){event.preventDefault();setBusy(true);setError('');setMessage('');
    if(newPassword!==confirm){setError('两次输入的新密码不一致');setBusy(false);return;}
    const response=await fetch('/api/learner-proxy/auth/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({old_password:oldPassword,new_password:newPassword})});
    setBusy(false);
    if(!response.ok){const data=await response.json().catch(()=>({detail:'修改失败，请检查原密码'}));setError(data.detail??'修改失败，请检查原密码');return;}
    setOldPassword('');setNewPassword('');setConfirm('');setMessage('密码已修改成功，其它设备上的登录已失效。');}
  return <section className="card"><h2>修改密码</h2><p className="muted">输入当前密码与新的密码即可生效；其它设备的登录状态会被清除。</p>
    <form className="reviewForm" onSubmit={submit}>
      <label>当前密码<input className="textInput" type="password" required value={oldPassword} onChange={e=>setOldPassword(e.target.value)} autoComplete="current-password"/></label>
      <label>新密码<input className="textInput" type="password" required value={newPassword} onChange={e=>setNewPassword(e.target.value)} autoComplete="new-password"/></label>
      <label>确认新密码<input className="textInput" type="password" required value={confirm} onChange={e=>setConfirm(e.target.value)} autoComplete="new-password"/></label>
      <div className="row" style={{justifyContent:'flex-start',gap:12}}><button className="button nativeButton" disabled={busy}>{busy?'保存中…':'保存新密码'}</button><button type="button" className="ghostButton" onClick={()=>router.push('/')}>返回首页</button></div>
      {message&&<p className="statusText" style={{color:'#067647'}}>{message}</p>}{error&&<p className="errorText">{error}</p>}
    </form>
  </section>;
}
