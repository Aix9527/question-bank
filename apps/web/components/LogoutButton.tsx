'use client';
import {useRouter} from 'next/navigation';
export default function LogoutButton(){const router=useRouter();async function logout(){await fetch('/api/session/logout',{method:'POST'});router.push('/login');router.refresh();}return <button className="ghostButton" onClick={logout}>退出登录</button>}
