'use client';

import { useState } from 'react';


export default function FavoriteButton({ questionId }: { questionId: number }) {
  const [state, setState] = useState<'idle'|'saving'|'saved'|'error'>('idle');

  async function save() {
    setState('saving');
    try {
      const response = await fetch(`/api/learner-proxy/questions/${questionId}/favorite`, { method: 'POST' });
      if (!response.ok) throw new Error('favorite failed');
      setState('saved');
    } catch {
      setState('error');
    }
  }

  return <button className="ghostButton" onClick={save} disabled={state === 'saving' || state === 'saved'}>
    {state === 'saving' ? '收藏中…' : state === 'saved' ? '✓ 已收藏' : state === 'error' ? '重试收藏' : '☆ 收藏题目'}
  </button>;
}
