import { cookies } from 'next/headers';

const INTERNAL_API_BASE = process.env.API_INTERNAL_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

export async function POST() {
  const jar = await cookies();
  const token = jar.get('qb_session')?.value;
  if (token) {
    await fetch(`${INTERNAL_API_BASE}/api/auth/logout`, {method:'POST', headers:{Authorization:`Bearer ${token}`}, cache:'no-store'}).catch(()=>undefined);
  }
  jar.delete('qb_session');
  return Response.json({ok:true});
}
