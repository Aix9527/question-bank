import { redirect } from 'next/navigation';

export default function LoginPage() {
  // 登录界面已移除，直接进入题库首页。
  redirect('/');
}
