import { redirect } from 'next/navigation';
import { apiGet } from '../../lib/server-api';

type Me = { id:number; username:string; role:'learner'|'admin' };

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  // Keep the v0.4 single-user/local workflow unchanged. In deployed auth mode,
  // the backend remains the source of truth and this guard only prevents a
  // learner from rendering administrator pages before the API returns 403.
  if ((process.env.QUESTION_BANK_AUTH_REQUIRED ?? '').toLowerCase() === 'true') {
    const me = await apiGet<Me>('/api/auth/me');
    if (me.role !== 'admin') redirect('/');
  }
  return children;
}
