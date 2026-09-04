function sanitizeStoredHtml(value:string):string{
  let html=value.replace(/<script\b[\s\S]*?<\/script>/gi,'').replace(/<style\b[\s\S]*?<\/style>/gi,'');
  html=html.replace(/<img\b[^>]*>/gi,(tag)=>{
    const match=tag.match(/\bsrc\s*=\s*(["'])(.*?)\1/i);
    const src=match?.[2]??'';
    if(!/^data:image\/(?:png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=]+$/i.test(src)) return '';
    return `<img class="inlineMedia" src="${src}" alt="题目图片" />`;
  });
  html=html.replace(/<br\b[^>]*>/gi,'<br>');
  // 放行安全的内联格式标签（含 <u> 划线还原、上下标与加粗/斜体）
  html=html.replace(/<(?!\/?(?:br|img|u|b|strong|i|em|sub|sup)\b)[^>]*>/gi,'');
  return html;
}

export default function RichHtml({html,className}:{html:string;className?:string}){
  return <span className={className} dangerouslySetInnerHTML={{__html:sanitizeStoredHtml(html)}}/>;
}
