import './globals.css';

export const metadata = { title: '专科复习在线题库', description: '语文、数学、英语在线刷题与批改' };

// suppressHydrationWarning: 部分浏览器扩展会在 React 水合前给 <html> 注入
// style（如 -webkit-touch-callout）导致属性级水合告警；此类外部注入无害，
// 这里显式忽略以免控制台误报。
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN" suppressHydrationWarning><body>{children}</body></html>;
}
