import { redirect } from 'next/navigation';

export default function RegisterPage() {
  // 登录/注册界面已移除，直接进入题库首页。
  redirect('/');
}
