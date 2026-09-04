import BackTop from '../../../components/BackTop';
import {apiGetAdmin} from '../../../lib/server-api';
import AdminUserManager from '../../../components/AdminUserManager';
type User={id:number;username:string;display_name:string|null;role:string;enabled:boolean};
export default async function UsersPage(){const users=await apiGetAdmin<User[]>('/api/admin/users');return <main className="shell"><BackTop href="/admin">← 返回管理后台</BackTop><section className="hero"><h1>用户与权限</h1><p>学习账号的数据彼此隔离；只有 admin 角色可以管理题库、批改、导入和备份。</p></section><AdminUserManager users={users}/></main>}
