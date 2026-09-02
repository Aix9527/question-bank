import Link from 'next/link';
import {apiGetAdmin} from '../../../../lib/server-api';
import AdminQuestionEditor from '../../../../components/AdminQuestionEditor';
type Question=Parameters<typeof AdminQuestionEditor>[0]['question'];
export default async function AdminQuestionPage({params}:{params:Promise<{id:string}>}){const {id}=await params;const question=await apiGetAdmin<Question>(`/api/admin/questions/${id}`);return <main className="shell"><section className="hero"><h1>编辑题目 #{id}</h1><p>保存任何修改都会递增 version；旧 `answer` 答案字段仍可判分，但新数据统一使用 `value`。</p></section><AdminQuestionEditor question={question}/><Link className="backLink" href="/admin/questions">← 返回题目管理</Link></main>}
