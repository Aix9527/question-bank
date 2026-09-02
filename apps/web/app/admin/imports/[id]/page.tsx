import Link from 'next/link';
import { apiGetAdmin } from '../../../../lib/server-api';
import ImportReviewEditor from '../../../../components/ImportReviewEditor';

type Warning={id:string;code:string;message:string;severity:string;candidate_id:string|null;resolved:boolean;resolution_note:string|null};
type Review={id:number;subject_code:string;source_filename:string;source_sha256:string;status:string;review_revision:number;draft:Record<string,unknown>;warnings:Warning[];blocking_warning_count:number};

export default async function ImportReviewPage({params}:{params:Promise<{id:string}>}){
  const {id}=await params; const review=await apiGetAdmin<Review>(`/api/admin/imports/${id}/review`);
  return <main className="shell"><section className="hero"><div className="eyebrow">Import #{review.id} · revision {review.review_revision}</div><h1>{String((review.draft as any).title??review.source_filename)}</h1><p>{review.source_filename}<br/><code>{review.source_sha256}</code></p></section><ImportReviewEditor review={review}/><Link className="backLink" href="/admin/imports">← 返回导入任务</Link></main>;
}
