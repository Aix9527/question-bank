import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const API_BASE = process.env.API_INTERNAL_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

async function authHeaders(admin=false): Promise<Record<string,string>> {
  const jar = await cookies();
  const session = jar.get('qb_session')?.value;
  const headers: Record<string,string> = {};
  if (session) headers.Authorization = `Bearer ${session}`;
  if (admin && !session && process.env.QUESTION_BANK_ADMIN_TOKEN) {
    headers['X-Admin-Token'] = process.env.QUESTION_BANK_ADMIN_TOKEN;
  }
  return headers;
}

async function request<T>(path:string, admin=false): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache:'no-store', headers: await authHeaders(admin) });
  if (response.status === 401) redirect('/login');
  if (response.status === 403 && admin) redirect('/');
  if (!response.ok) throw new Error(`${admin?'ADMIN ':''}API ${response.status}: ${path}`);
  return response.json() as Promise<T>;
}

export function apiGet<T>(path:string): Promise<T> { return request<T>(path, false); }
export function apiGetAdmin<T>(path:string): Promise<T> { return request<T>(path, true); }
