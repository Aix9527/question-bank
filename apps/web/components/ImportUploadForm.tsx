'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function ImportUploadForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setMessage('');
    const form = event.currentTarget;
    const body = new FormData(form);
    try {
      const response = await fetch('/api/admin-proxy/imports/docx', { method:'POST', body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? `HTTP ${response.status}`);
      setMessage(payload.reused ? '该源文件已存在，已打开原导入任务。' : '解析完成，已进入审核队列。');
      form.reset();
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '上传失败');
    } finally { setBusy(false); }
  }

  return <form className="card reviewForm" onSubmit={submit}>
    <h2>上传 DOCX</h2>
    <label>科目<select name="subject_code" className="textInput" defaultValue="chinese"><option value="chinese">语文</option><option value="math">数学</option><option value="english">英语</option></select></label>
    <label>试卷文件<input name="file" className="textInput" type="file" accept=".docx" required /></label>
    <button className="button nativeButton" disabled={busy}>{busy?'解析中…':'解析并进入审核'}</button>
    {message && <p className="muted">{message}</p>}
  </form>;
}
