import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

const INTERNAL_API_BASE = process.env.API_INTERNAL_BASE ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

export async function POST(request:NextRequest) {
  const body = await request.text();
  const response = await fetch(`${INTERNAL_API_BASE}/api/auth/register`, {method:'POST', headers:{'Content-Type':'application/json'}, body, cache:'no-store'});
  const payload = await response.arrayBuffer();
  if (response.ok) {
    const parsed = JSON.parse(Buffer.from(payload).toString('utf8')) as {token:string;expires_at:string;user:unknown};
    const expires = new Date(parsed.expires_at);
    (await cookies()).set('qb_session', parsed.token, {httpOnly:true, sameSite:'lax', secure:(process.env.QUESTION_BANK_COOKIE_SECURE??'false').toLowerCase()==='true', path:'/', expires});
    return Response.json({user:parsed.user});
  }
  return new Response(payload, {status:response.status, headers:{'content-type':response.headers.get('content-type')??'application/json'}});
}
