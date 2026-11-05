export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  // 登录界面已移除：管理端与学习端统一使用本地访客身份，直接渲染。
  return children;
}
