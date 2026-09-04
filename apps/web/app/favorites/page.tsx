import BackTop from '../../components/BackTop';
import { apiGet } from '../../lib/server-api';
import RemoveFavoriteButton from '../../components/RemoveFavoriteButton';
import RichHtml from '../../components/RichHtml';

type Favorite={id:number;question_id:number;created_at:string;question:{stem_html:string;material_html:string|null;type:string;score:number;knowledge_points:string[]|null}};
export default async function FavoritesPage(){const items=await apiGet<Favorite[]>('/api/me/favorites');return <main className="shell"><BackTop href="/">← 返回首页</BackTop><section className="hero"><h1>收藏题</h1><p>收藏不会影响错题状态，可作为自己的重点题单长期保留。</p></section><div className="list">{items.length===0&&<div className="card"><strong>暂时没有收藏题</strong><p className="muted">在试卷详情中点击“收藏题目”即可加入。</p></div>}{items.map(item=><article className="card" key={item.id}><div className="row"><strong>{item.question.type}</strong><RemoveFavoriteButton questionId={item.question_id}/></div>{item.question.material_html&&<div className="materialBox"><RichHtml html={item.question.material_html}/></div>}<h3><RichHtml html={item.question.stem_html}/></h3><p className="muted">{item.question.score} 分 {item.question.knowledge_points?.length?`· ${item.question.knowledge_points.join(' / ')}`:''}</p></article>)}</div></main>}
