import BackTop from '../../components/BackTop';
import { apiGet } from '../../lib/server-api';
import PasswordChangeForm from '../../components/PasswordChangeForm';

type Me = { id:number; username:string; display_name:string|null; role:string };

export default async function PasswordPage(){
  const me = await apiGet<Me>('/api/auth/me');
  return <main className="shell"><BackTop href="/">← 返回首页</BackTop><section className="hero"><h1>账号安全</h1><p>{me.display_name??me.username} · @{me.username} · {me.role==='admin'?'管理员':'学习账号'}</p></section><PasswordChangeForm/></main>;
}
