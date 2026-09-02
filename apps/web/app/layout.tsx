import './globals.css';

export const metadata = { title: '专科复习在线题库', description: '语文、数学、英语在线刷题与批改' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
