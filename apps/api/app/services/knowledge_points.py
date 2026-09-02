from __future__ import annotations

import html
import re


def _plain(*parts: str | None) -> str:
    value = ' '.join(part or '' for part in parts)
    value = re.sub(r'<[^>]+>', ' ', value)
    return html.unescape(value).strip()


def infer_knowledge_points(
    subject_code: str,
    question_type: str,
    stem_html: str | None,
    material_html: str | None,
    section_title: str | None,
) -> list[str]:
    text = _plain(stem_html, material_html)
    section = _plain(section_title)

    if subject_code == 'chinese':
        if question_type == 'essay' or '写作' in section:
            return ['语文/写作/作文']
        if '现代文阅读' in section:
            points = ['语文/阅读/现代文']
            if question_type in {'short_answer', 'translation'}:
                points.append('语文/阅读/简答')
            elif question_type == 'single_choice':
                points.append('语文/阅读/信息理解')
            return points
        if '古代诗文' in section or '古诗文' in section:
            if question_type == 'translation' or '翻译' in text:
                return ['语文/古诗文/文言翻译']
            if question_type == 'poetry' or any(key in text for key in ('诗', '词', '赏析')):
                return ['语文/古诗文/诗歌鉴赏']
            return ['语文/古诗文/文言阅读']
        rules = (
            (('注音', '读音', '拼音'), '语文/基础知识/字音'),
            (('错别字', '字形'), '语文/基础知识/字形'),
            (('成语',), '语文/基础知识/成语'),
            (('语病', '病句'), '语文/基础知识/病句辨析'),
            (('排序', '连贯', '衔接'), '语文/基础知识/语言连贯'),
            (('词语', '依次填入', '填入下列'), '语文/基础知识/词语运用'),
            (('文学常识', '作家', '作品'), '语文/基础知识/文学常识'),
        )
        for keywords, point in rules:
            if any(keyword in text for keyword in keywords):
                return [point]
        return ['语文/基础知识/综合'] if question_type == 'single_choice' else ['语文/综合']

    if subject_code == 'math':
        normalized = text.lower().replace(' ', '')
        rules = (
            (('集合', '∪', '∩', '子集'), '数学/集合'),
            (('sin', 'cos', 'tan', '三角函数', '三角比'), '数学/三角函数'),
            (('不等式', '绝对值', '|x', '|2x'), '数学/不等式'),
            (('直线', '圆', '轨迹', '斜率', '距离', '交点', '坐标'), '数学/解析几何'),
            (('概率', '随机', '排列', '组合', '取出', '组成两位数'), '数学/概率与计数'),
            (('数列', '等差', '等比'), '数学/数列'),
            (('导数', '极值', '单调区间'), '数学/导数'),
            (('向量',), '数学/向量'),
            (('三角形', '全等', '相似', '面积'), '数学/平面几何'),
            (('函数', 'lg', 'log', '定义域', '值域', '图像'), '数学/函数'),
        )
        for keywords, point in rules:
            if any(keyword.lower() in normalized for keyword in keywords):
                return [point]
        suffix = {'single_choice': '选择题', 'fill_blank': '填空题', 'solution': '解答题'}.get(question_type, '综合')
        return [f'数学/综合/{suffix}']

    if subject_code == 'english':
        lower = text.lower()
        if '语音' in section:
            return ['英语/语音']
        if '完形' in section:
            return ['英语/完形填空']
        if '阅读理解' in section:
            return ['英语/阅读理解']
        if '补全对话' in section:
            return ['英语/补全对话']
        if question_type == 'essay' or '书面表达' in section or '写作' in section:
            return ['英语/写作']
        if '词汇与语法' in section:
            if (re.search(r'\b(which|that|who|whom|whose|where)\b', lower) and ('____' in text or '___' in text)) or re.search(r'\b\w+\s+_{3,}\s+(?:we|you|he|she|they|i)\b', lower):
                return ['英语/语法/定语从句']
            if re.search(r'\bif\b', lower) and ('will ' in lower or 'would ' in lower or 'tomorrow' in lower):
                return ['英语/语法/条件状语从句']
            if re.search(r'\b(decide|want|hope|plan|enjoy|finish|avoid|mind)\w*\b', lower) and ('____' in text or '___' in text):
                return ['英语/语法/非谓语动词']
            if any(token in lower for token in ('yesterday', 'last ', 'since ', 'already', 'twice a week', 'tomorrow')):
                return ['英语/语法/时态']
            return ['英语/词汇与语法/综合']
        return ['英语/综合']

    return []
