'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';


export default function RemoveFavoriteButton({ questionId }: { questionId: number }) {
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function remove() {
    setBusy(true);
    const response = await fetch(`/api/learner-proxy/questions/${questionId}/favorite`, { method: 'DELETE' });
    setBusy(false);
    if (response.ok) router.refresh();
  }

  return <button className="ghostButton danger" onClick={remove} disabled={busy}>{busy ? '移除中…' : '取消收藏'}</button>;
}
