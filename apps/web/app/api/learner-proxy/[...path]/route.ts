import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

const INTERNAL_API_BASE = process.env.API_INTERNAL_BASE ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000';

async function proxy(request: NextRequest, paramsPromise: Promise<{path:string[]}>) {
  const {path} = await paramsPromise;
  const incoming = new URL(request.url);
  const target = new URL(`/api/${path.join('/')}`, INTERNAL_API_BASE);
  target.search = incoming.search;
  const headers = new Headers();
  const contentType = request.headers.get('content-type');
  if (contentType) headers.set('content-type', contentType);
  const token = (await cookies()).get('qb_session')?.value;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const method = request.method;
  const body = method === 'GET' || method === 'HEAD' ? undefined : await request.arrayBuffer();
  const response = await fetch(target, {method, headers, body, cache:'no-store'});
  const responseHeaders = new Headers();
  const responseType = response.headers.get('content-type');
  if (responseType) responseHeaders.set('content-type', responseType);
  return new Response(await response.arrayBuffer(), {status:response.status, headers:responseHeaders});
}

export async function GET(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
export async function POST(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
export async function PATCH(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
export async function DELETE(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){return proxy(request,params)}
