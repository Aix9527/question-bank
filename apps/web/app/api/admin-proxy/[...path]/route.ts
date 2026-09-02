import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

const INTERNAL_API_BASE = process.env.API_INTERNAL_BASE ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

async function proxy(request: NextRequest, paramsPromise: Promise<{path:string[]}>) {
  const {path} = await paramsPromise;
  const incoming = new URL(request.url);
  const target = new URL(`/api/admin/${path.join('/')}`, INTERNAL_API_BASE);
  target.search = incoming.search;
  const headers = new Headers();
  const contentType = request.headers.get('content-type');
  if (contentType) headers.set('content-type', contentType);
  const session = (await cookies()).get('qb_session')?.value;
  if (session) headers.set('Authorization', `Bearer ${session}`);
  else if (process.env.QUESTION_BANK_ADMIN_TOKEN) headers.set('X-Admin-Token', process.env.QUESTION_BANK_ADMIN_TOKEN);

  const method = request.method;
  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();
  const response = await fetch(target, { method, headers, body, cache:'no-store' });
  const responseHeaders = new Headers();
  for (const name of ['content-type','content-disposition']) {
    const value = response.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(await response.arrayBuffer(), {status:response.status, headers:responseHeaders});
}

export async function GET(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
export async function POST(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
export async function PATCH(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
export async function DELETE(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
