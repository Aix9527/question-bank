from __future__ import annotations

import copy
import html
import re
from typing import Any

SECTION_RE = re.compile(r'^[一二三四五六七八九十]+、')
ANSWER_RE = re.compile(r'^(?:答案|【答案】|\[答案\])\s*[:：]?\s*(.*)$')
REFERENCE_RE = re.compile(r'^【参考答案】\s*(.*)$')
REFERENCE_ESSAY_RE = re.compile(r'^【参考范文】\s*(.*)$')
EXPLANATION_RE = re.compile(r'^(?:解析|【解析】)\s*[:：]?\s*(.*)$')
QUESTION_RE = re.compile(r'^(\d+)[\.．、]\s*(.*)$')
DOT_QUESTION_RE = re.compile(r'^(\d+)[\.．]\s*(.*)$')
SUBQUESTION_RE = re.compile(r'^[（(](\d+)[）)]\s*(.*)$')
BARE_QUESTION_RE = re.compile(r'^(\d+)[\.．]\s*$')
OPTION_START_RE = re.compile(r'^\s*([A-H])(?:[\.．、]\s*|\s+(?=[xyzXYZfF\d(（±√]))(.*)$', re.S)
OPTION_SPLIT_RE = re.compile(r'(?:^|\n|\s{2,})([A-H])(?:[\.．、]\s*|\s+(?=[xyzXYZfF\d(（±√]))', re.M)
NUMBERED_A_OPTION_RE = re.compile(r'^(\d+)[.．]\s*A[.．、]\s*(.*)$', re.S)


def _entry_text(entry: dict[str, Any]) -> str:
    return (entry.get('text') or '').strip()


def _entry_html(entry: dict[str, Any]) -> str:
    return entry.get('html') or html.escape(entry.get('text') or '')


def _join_html(entries: list[dict[str, Any]]) -> str | None:
    values = [_entry_html(entry) for entry in entries if _entry_html(entry).strip()]
    return '<br>'.join(values) if values else None


def _join_text(entries: list[dict[str, Any]]) -> str:
    return '\n'.join(_entry_text(entry) for entry in entries if _entry_text(entry))


def _document_lines(ast: dict[str, Any]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for block in ast.get('blocks', []):
        text = _entry_text(block)
        block_html = _entry_html(block)
        if block.get('kind') == 'paragraph' and (text or '<img ' in block_html):
            lines.append(block)
        elif block.get('kind') == 'table' and (text or block.get('rows')):
            lines.append(block)
    return lines


def _parse_answer(text: str) -> str | None:
    m = ANSWER_RE.match(text.strip())
    if not m:
        return None
    value = m.group(1).strip()
    return value or None


def _parse_reference(text: str) -> str | None:
    m = REFERENCE_RE.match(text.strip())
    if not m:
        return None
    value = m.group(1).strip()
    return value or None


def _parse_explanation(text: str) -> str | None:
    m = EXPLANATION_RE.match(text.strip())
    if not m:
        return None
    return m.group(1).strip()


def _starts_option(text: str) -> bool:
    return OPTION_START_RE.match(text) is not None


def _options_from_entries(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int | None]:
    first_index: int | None = None
    options: list[dict[str, Any]] = []
    for eidx, entry in enumerate(entries):
        text = entry.get('text') or ''
        matches = list(OPTION_SPLIT_RE.finditer(text))
        if not matches:
            m = OPTION_START_RE.match(text)
            if m:
                matches = [m]
        if not matches:
            continue
        if first_index is None:
            first_index = eidx

        # Single option paragraph: preserve inline DOCX image HTML if present.
        direct = OPTION_START_RE.match(text)
        if direct and len(matches) == 1:
            label = direct.group(1)
            content_text = direct.group(2).strip()
            content_html = _entry_html(entry)
            content_html = re.sub(
                rf'^\s*{label}(?:[\.．、]\s*|\s+)', '', content_html, count=1, flags=re.I
            ).strip()
            options.append({
                'label': label,
                'content_html': content_html or html.escape(content_text),
                'order_index': len(options) + 1,
            })
            continue

        # Multiple options in one paragraph: split text; these source documents do not
        # place inline images in such combined option lines.
        if matches and hasattr(matches[0], 'start'):
            for midx, match in enumerate(matches):
                start = match.end()
                end = matches[midx + 1].start() if midx + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                label = match.group(1)
                options.append({
                    'label': label,
                    'content_html': html.escape(content),
                    'order_index': len(options) + 1,
                })
    return options, first_index


def _section_score(title: str) -> float | None:
    for pattern in (r'每题\s*(\d+(?:\.\d+)?)\s*分', r'(\d+(?:\.\d+)?)\s*分\s*/\s*个'):
        m = re.search(pattern, title)
        if m:
            return float(m.group(1))
    return None


def _standalone_score(title: str) -> float | None:
    m = re.search(r'[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]', title)
    return float(m.group(1)) if m else None


def _score_sequence(title: str) -> list[float]:
    # e.g. 三、解答题（3题，12分、16分、17分）
    marker = re.search(r'\d+题[，,]\s*([^）)]*)', title)
    if not marker:
        return []
    return [float(v) for v in re.findall(r'(\d+(?:\.\d+)?)\s*分', marker.group(1))]


def _instruction_scores(text: str, count: int) -> list[float]:
    scores: dict[int, float] = {}
    for m in re.finditer(r'第([0-9、，,]+)题各\s*(\d+(?:\.\d+)?)\s*分', text):
        value = float(m.group(2))
        for raw in re.split(r'[、，,]', m.group(1)):
            if raw.strip().isdigit():
                scores[int(raw.strip())] = value
    for m in re.finditer(r'第(\d+)题\s*(\d+(?:\.\d+)?)\s*分', text):
        scores[int(m.group(1))] = float(m.group(2))
    return [scores.get(index, 0.0) for index in range(1, count + 1)]


def _make_warning(
    warnings: list[dict[str, Any]], code: str, message: str, *,
    severity: str = 'review', candidate_id: str | None = None,
) -> None:
    warnings.append({
        'id': f'w{len(warnings) + 1}',
        'code': code,
        'message': message,
        'severity': severity,
        'candidate_id': candidate_id,
        'resolved': False,
        'resolution_note': None,
    })


def _answer_from_explanation(explanation: str | None) -> str | None:
    if not explanation:
        return None
    matches = re.findall(
        r'(?:故(?:本题)?选|正确答案(?:为|是)|应选)\s*[“"\']?([A-H])',
        explanation,
        flags=re.I,
    )
    return matches[-1].upper() if matches else None


def _external_number(entries: list[dict[str, Any]]) -> str | None:
    for entry in entries:
        text = _entry_text(entry)
        for regex in (QUESTION_RE, SUBQUESTION_RE):
            match = regex.match(text)
            if match:
                return match.group(1)
    return None


def _make_choice_candidate(
    stem_entries: list[dict[str, Any]], option_entries: list[dict[str, Any]], answer: str | None,
    explanation_html: str | None, *, candidate_id: str, score: float,
    warnings: list[dict[str, Any]], material_html: str | None = None,
    external_number: str | None = None,
) -> dict[str, Any]:
    options, _ = _options_from_entries(option_entries)
    if not options:
        _make_warning(warnings, 'missing_options', '选择题未识别到选项。', severity='blocking', candidate_id=candidate_id)
    if not answer:
        _make_warning(warnings, 'missing_answer', '选择题未识别到标准答案。', severity='blocking', candidate_id=candidate_id)

    plain_explanation = re.sub(r'<[^>]+>', '', explanation_html or '')
    inferred = _answer_from_explanation(html.unescape(plain_explanation))
    normalized_answer = answer.upper() if answer else None
    if normalized_answer and inferred and inferred != normalized_answer:
        _make_warning(
            warnings,
            'answer_explanation_conflict',
            f'答案标记为 {normalized_answer}，但解析文字指向 {inferred}。',
            severity='blocking',
            candidate_id=candidate_id,
        )

    return {
        'candidate_id': candidate_id,
        'external_number': external_number or _external_number(stem_entries),
        'type': 'single_choice',
        'stem_html': _join_html(stem_entries) or (f'第{external_number}题' if external_number else '题目'),
        'material_html': material_html,
        'answer_mode': 'exact',
        'standard_answer_json': {'value': normalized_answer} if normalized_answer else None,
        'explanation_html': explanation_html,
        'score': float(score),
        'difficulty': None,
        'knowledge_points': None,
        'options': options,
        'source_block_indexes': [entry.get('index') for entry in stem_entries + option_entries],
    }


def _make_manual_candidate(
    stem_entries: list[dict[str, Any]], reference_html: str | None, *, candidate_id: str,
    qtype: str, score: float, material_html: str | None = None,
    external_number: str | None = None,
) -> dict[str, Any]:
    return {
        'candidate_id': candidate_id,
        'external_number': external_number or _external_number(stem_entries),
        'type': qtype,
        'stem_html': _join_html(stem_entries) or (f'第{external_number}题' if external_number else '题目'),
        'material_html': material_html,
        'answer_mode': 'manual',
        'standard_answer_json': {'reference_html': reference_html} if reference_html else None,
        'explanation_html': reference_html,
        'score': float(score),
        'difficulty': None,
        'knowledge_points': None,
        'options': [],
        'source_block_indexes': [entry.get('index') for entry in stem_entries],
    }


def _make_fill_candidate(
    stem_entries: list[dict[str, Any]], answer: str | None, *, candidate_id: str, score: float,
) -> dict[str, Any]:
    if not answer:
        standard = None
    else:
        standard = {'value': answer}
    return {
        'candidate_id': candidate_id,
        'external_number': _external_number(stem_entries),
        'type': 'fill_blank',
        'stem_html': _join_html(stem_entries) or '填空题',
        'material_html': None,
        'answer_mode': 'normalized_text',
        'standard_answer_json': standard,
        'explanation_html': None,
        'score': float(score),
        'difficulty': None,
        'knowledge_points': None,
        'options': [],
        'source_block_indexes': [entry.get('index') for entry in stem_entries],
    }


def _next_question_index(entries: list[dict[str, Any]], start: int) -> int:
    for idx in range(start, len(entries)):
        if QUESTION_RE.match(_entry_text(entries[idx])):
            return idx
    return len(entries)


def _explode_embedded_numbered_questions(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split source paragraphs where a numbered question was pasted after an explanation.

    We deliberately scope this repair to explanation paragraphs. A bare ``7.`` in normal prose
    is therefore never treated as a structural boundary.
    """
    expanded: list[dict[str, Any]] = []
    pattern = re.compile(r'(?<=[。.!?])\s*(\d{1,2}[.．]\s*\S.*)$', re.S)
    for entry in entries:
        text = _entry_text(entry)
        if not EXPLANATION_RE.match(text):
            expanded.append(entry)
            continue
        match = pattern.search(text)
        if not match:
            expanded.append(entry)
            continue
        first_text = text[:match.start()].strip()
        second_text = match.group(1).strip()
        first = dict(entry)
        first['text'] = first_text
        first['html'] = html.escape(first_text)
        second = dict(entry)
        second['text'] = second_text
        second['html'] = html.escape(second_text)
        second['virtual_split'] = True
        expanded.extend([first, second])
    return expanded


def _parse_standard_answer_section(
    entries: list[dict[str, Any]], *, qtype: str, default_score: float,
    score_sequence: list[float], section_index: int, warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    cursor = 0
    i = 0
    while i < len(entries):
        answer_match = ANSWER_RE.match(_entry_text(entries[i]))
        if not answer_match:
            i += 1
            continue
        q_order = len(questions) + 1
        answer = answer_match.group(1).strip() or None
        content = entries[cursor:i]
        score = score_sequence[q_order - 1] if q_order - 1 < len(score_sequence) else default_score

        # Explanation/reference may span image-only paragraphs until the next numbered question.
        j = i + 1
        post_entries: list[dict[str, Any]] = []
        if j < len(entries) and EXPLANATION_RE.match(_entry_text(entries[j])):
            post_entries = [entries[j]]
            j += 1
            # Preserve formula/image-only paragraphs attached to the explanation without
            # swallowing the next unnumbered question.
            while j < len(entries) and not _entry_text(entries[j]) and '<img ' in _entry_html(entries[j]):
                post_entries.append(entries[j])
                j += 1
        elif qtype == 'solution':
            j2 = _next_question_index(entries, j)
            post_entries = entries[j:j2]
            j = j2

        if qtype == 'single_choice':
            options, first_opt = _options_from_entries(content)
            if first_opt is None:
                stem_entries = content
                option_entries: list[dict[str, Any]] = []
            else:
                stem_entries = content[:first_opt]
                option_entries = content[first_opt:]
            explanation_html = _join_html(post_entries)
            questions.append(_make_choice_candidate(
                stem_entries, option_entries, answer, explanation_html,
                candidate_id=f's{section_index}q{q_order}', score=score, warnings=warnings,
            ))
        elif qtype == 'fill_blank':
            questions.append(_make_fill_candidate(
                content, answer, candidate_id=f's{section_index}q{q_order}', score=score
            ))
        else:
            reference_parts: list[str] = []
            if answer:
                reference_parts.append(html.escape(answer))
            if post_entries:
                ref_html = _join_html(post_entries)
                if ref_html:
                    reference_parts.append(ref_html)
            questions.append(_make_manual_candidate(
                content,
                '<br>'.join(reference_parts) if reference_parts else None,
                candidate_id=f's{section_index}q{q_order}', qtype='solution', score=score,
            ))
        cursor = j
        i = j
    return questions


def _normalize_cloze_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        match = NUMBERED_A_OPTION_RE.match(_entry_text(entry))
        if not match:
            normalized.append(entry)
            continue
        virtual = dict(entry)
        content = match.group(2).strip()
        virtual['text'] = f'A. {content}'
        virtual['html'] = f'A. {html.escape(content)}'
        virtual['cloze_number'] = match.group(1)
        normalized.append(virtual)
    return normalized


def _parse_english_cloze(
    entries: list[dict[str, Any]], *, section_index: int, score: float,
    warnings: list[dict[str, Any]], start_number: int = 21,
) -> list[dict[str, Any]]:
    entries = _normalize_cloze_entries(entries)
    first_option = next((i for i, entry in enumerate(entries) if _starts_option(_entry_text(entry))), len(entries))
    material_html = _join_html(entries[:first_option])
    questions: list[dict[str, Any]] = []
    cursor = first_option
    i = first_option
    while i < len(entries):
        answer_match = ANSWER_RE.match(_entry_text(entries[i]))
        if not answer_match:
            i += 1
            continue
        q_order = len(questions) + 1
        qnum = start_number + q_order - 1
        answer = answer_match.group(1).strip() or None
        option_entries = entries[cursor:i]
        j = i + 1
        explanation_entries: list[dict[str, Any]] = []
        if j < len(entries) and EXPLANATION_RE.match(_entry_text(entries[j])):
            explanation_entries.append(entries[j])
            j += 1
        stem_entry = {
            'index': option_entries[0].get('index') if option_entries else None,
            'text': f'第{qnum}空',
            'html': f'第{qnum}空',
        }
        questions.append(_make_choice_candidate(
            [stem_entry], option_entries, answer, _join_html(explanation_entries),
            candidate_id=f's{section_index}q{q_order}', score=score, warnings=warnings,
            material_html=material_html, external_number=str(qnum),
        ))
        cursor = j
        i = j
    return questions


def _reading_choice_parts(
    content: list[dict[str, Any]], current_material: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    options, first_opt = _options_from_entries(content)

    # Some source papers omit A/B/C/D labels entirely for the first question of a passage.
    # In that shape the final five paragraphs are: stem + four option texts.
    if not options and len(content) >= 5:
        pre = content[:-5]
        stem_entries = [content[-5]]
        raw_options = content[-4:]
        option_entries: list[dict[str, Any]] = []
        for label, entry in zip('ABCD', raw_options, strict=True):
            virtual = dict(entry)
            virtual['text'] = f'{label}. {_entry_text(entry)}'
            virtual['html'] = f'{label}. {_entry_html(entry)}'
            option_entries.append(virtual)
        if pre:
            current_material = _join_html(pre)
        return stem_entries, option_entries, current_material

    # Another malformed shape has only the final option labelled (usually D). Recover the
    # immediately preceding unlabeled option texts when their count matches the missing labels.
    if options and first_opt is not None and len(options) < 4:
        first_label = options[0]['label']
        missing = ord(first_label) - ord('A')
        if missing > 0 and first_opt >= missing + 1:
            pre = content[:first_opt - missing]
            raw_missing = content[first_opt - missing:first_opt]
            option_entries = []
            for offset, entry in enumerate(raw_missing):
                label = chr(ord('A') + offset)
                virtual = dict(entry)
                virtual['text'] = f'{label}. {_entry_text(entry)}'
                virtual['html'] = f'{label}. {_entry_html(entry)}'
                option_entries.append(virtual)
            option_entries.extend(content[first_opt:])
            if len(pre) > 1:
                current_material = _join_html(pre[:-1])
                stem_entries = [pre[-1]]
            else:
                stem_entries = pre
            return stem_entries, option_entries, current_material

    if first_opt is None:
        return content, [], current_material
    pre = content[:first_opt]
    option_entries = content[first_opt:]
    if len(pre) > 1:
        current_material = _join_html(pre[:-1])
        stem_entries = [pre[-1]]
    else:
        stem_entries = pre
    return stem_entries, option_entries, current_material


def _parse_reading_choices(
    entries: list[dict[str, Any]], *, section_index: int, score: float,
    warnings: list[dict[str, Any]], start_number: int,
) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    cursor = 0
    current_material: str | None = None
    i = 0
    while i < len(entries):
        answer_match = ANSWER_RE.match(_entry_text(entries[i]))
        if not answer_match:
            i += 1
            continue
        q_order = len(questions) + 1
        qnum = start_number + q_order - 1
        answer = answer_match.group(1).strip() or None
        content = entries[cursor:i]
        stem_entries, option_entries, current_material = _reading_choice_parts(content, current_material)
        j = i + 1
        explanation_entries: list[dict[str, Any]] = []
        if j < len(entries) and EXPLANATION_RE.match(_entry_text(entries[j])):
            explanation_entries.append(entries[j])
            j += 1
        questions.append(_make_choice_candidate(
            stem_entries, option_entries, answer, _join_html(explanation_entries),
            candidate_id=f's{section_index}q{q_order}', score=score, warnings=warnings,
            material_html=current_material, external_number=str(qnum),
        ))
        cursor = j
        i = j
    return questions


def _parse_english_completion(
    entries: list[dict[str, Any]], *, section_index: int, score: float,
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    first_bare = next((i for i, entry in enumerate(entries) if BARE_QUESTION_RE.match(_entry_text(entry))), len(entries))
    common = entries[:first_bare]
    first_option = next((i for i, entry in enumerate(common) if _starts_option(_entry_text(entry))), len(common))
    material_entries = common[:first_option]
    shared_option_entries = common[first_option:]
    shared_options, _ = _options_from_entries(shared_option_entries)
    material_html = _join_html(material_entries)

    questions: list[dict[str, Any]] = []
    i = first_bare
    while i < len(entries):
        bare = BARE_QUESTION_RE.match(_entry_text(entries[i]))
        if not bare:
            i += 1
            continue
        qnum = int(bare.group(1))
        answer = None
        explanation_entries: list[dict[str, Any]] = []
        j = i + 1
        if j < len(entries):
            match = ANSWER_RE.match(_entry_text(entries[j]))
            if match:
                answer = match.group(1).strip() or None
                j += 1
        if j < len(entries) and EXPLANATION_RE.match(_entry_text(entries[j])):
            explanation_entries.append(entries[j])
            j += 1

        stem_text = f'第{qnum}空'
        for entry in material_entries:
            text = _entry_text(entry)
            if re.search(rf'\b{qnum}[\.．]\s*_+', text):
                stem_text = text
                break
        candidate_id = f's{section_index}q{len(questions) + 1}'
        normalized_answer = answer.upper() if answer else None
        if not normalized_answer:
            _make_warning(warnings, 'missing_answer', f'第{qnum}空未识别到答案。', severity='blocking', candidate_id=candidate_id)
        questions.append({
            'candidate_id': candidate_id,
            'external_number': str(qnum),
            'type': 'single_choice',
            'stem_html': html.escape(stem_text),
            'material_html': material_html,
            'answer_mode': 'exact',
            'standard_answer_json': {'value': normalized_answer} if normalized_answer else None,
            'explanation_html': _join_html(explanation_entries),
            'score': float(score),
            'difficulty': None,
            'knowledge_points': None,
            'options': copy.deepcopy(shared_options),
            'source_block_indexes': [entries[i].get('index')],
        })
        i = j
    return questions


def _parse_english_essay(entries: list[dict[str, Any]], *, section_index: int, score: float) -> list[dict[str, Any]]:
    answer_idx = next((i for i, entry in enumerate(entries) if ANSWER_RE.match(_entry_text(entry))), len(entries))
    stem_entries = entries[:answer_idx]
    reference_entries = entries[answer_idx + 1:] if answer_idx < len(entries) else []
    reference_html = _join_html(reference_entries)
    return [_make_manual_candidate(
        stem_entries, reference_html, candidate_id=f's{section_index}q1', qtype='essay', score=score,
        external_number='56',
    )]


def _parse_subjective_segments(
    entries: list[dict[str, Any]], *, section_index: int, material_html: str | None,
    scores: list[float], qtype: str = 'short_answer', start_pattern: re.Pattern[str] = QUESTION_RE,
) -> list[dict[str, Any]]:
    starts = [i for i, entry in enumerate(entries) if start_pattern.match(_entry_text(entry))]
    questions: list[dict[str, Any]] = []
    for qidx, start in enumerate(starts):
        end = starts[qidx + 1] if qidx + 1 < len(starts) else len(entries)
        segment = entries[start:end]
        stem_entries: list[dict[str, Any]] = []
        reference_parts: list[str] = []
        for entry in segment:
            text = _entry_text(entry)
            am = ANSWER_RE.match(text)
            rm = REFERENCE_RE.match(text)
            if am or rm:
                value = (am or rm).group(1).strip()
                if value:
                    reference_parts.append(html.escape(value))
                # Preserve inline images on an answer line.
                if '<img ' in _entry_html(entry):
                    reference_parts.append(_entry_html(entry))
            else:
                stem_entries.append(entry)
        score = scores[qidx] if qidx < len(scores) else 0.0
        ext = _external_number(stem_entries) or str(qidx + 1)
        questions.append(_make_manual_candidate(
            stem_entries,
            '<br>'.join(reference_parts) if reference_parts else None,
            candidate_id=f's{section_index}q{qidx + 1}', qtype=qtype, score=score,
            material_html=material_html, external_number=ext,
        ))
    return questions


def _parse_chinese_modern(
    entries: list[dict[str, Any]], *, section_index: int, warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    second_idx = next(
        (i for i, entry in enumerate(entries) if re.match(r'^2[、.]\s*阅读', _entry_text(entry))),
        len(entries),
    )
    objective_part = entries[:second_idx]
    subjective_part = entries[second_idx:]
    objective = _parse_reading_choices(
        objective_part, section_index=section_index, score=4.0, warnings=warnings, start_number=1,
    )

    if not subjective_part:
        return objective
    instruction = _entry_text(subjective_part[0])
    qstarts = [i for i, entry in enumerate(subjective_part) if DOT_QUESTION_RE.match(_entry_text(entry))]
    first_q = qstarts[0] if qstarts else len(subjective_part)
    material_html = _join_html(subjective_part[:first_q])
    scores = _instruction_scores(instruction, len(qstarts))
    subjective = _parse_subjective_segments(
        subjective_part[first_q:], section_index=section_index,
        material_html=material_html, scores=scores, qtype='short_answer', start_pattern=DOT_QUESTION_RE,
    )
    # Candidate IDs must stay unique inside a section.
    for offset, question in enumerate(subjective, start=len(objective) + 1):
        question['candidate_id'] = f's{section_index}q{offset}'
    return objective + subjective


def _parse_chinese_classical(
    entries: list[dict[str, Any]], *, section_index: int, warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    poem_idx = next((i for i, entry in enumerate(entries) if re.match(r'^2[\.．、]\s*阅读古诗', _entry_text(entry))), len(entries))
    prose = entries[:poem_idx]
    poem = entries[poem_idx:]
    questions: list[dict[str, Any]] = []

    prose_starts = [i for i, entry in enumerate(prose) if SUBQUESTION_RE.match(_entry_text(entry))]
    first_q = prose_starts[0] if prose_starts else len(prose)
    prose_material = _join_html(prose[:first_q])
    prose_instruction = _entry_text(prose[0]) if prose else ''
    prose_scores = _instruction_scores(prose_instruction, len(prose_starts))
    for qidx, start in enumerate(prose_starts):
        end = prose_starts[qidx + 1] if qidx + 1 < len(prose_starts) else len(prose)
        segment = prose[start:end]
        score = prose_scores[qidx] if qidx < len(prose_scores) else 0.0
        options, first_opt = _options_from_entries(segment)
        if options and first_opt is not None:
            answer_idx = next((i for i, entry in enumerate(segment) if ANSWER_RE.match(_entry_text(entry))), len(segment))
            answer = _parse_answer(_entry_text(segment[answer_idx])) if answer_idx < len(segment) else None
            stem_entries = segment[:first_opt]
            option_entries = segment[first_opt:answer_idx]
            explanation_entries = segment[answer_idx + 1:] if answer_idx < len(segment) else []
            questions.append(_make_choice_candidate(
                stem_entries, option_entries, answer, _join_html(explanation_entries),
                candidate_id=f's{section_index}q{len(questions)+1}', score=score, warnings=warnings,
                material_html=prose_material, external_number=str(qidx + 1),
            ))
        else:
            stem_entries: list[dict[str, Any]] = []
            refs: list[str] = []
            for entry in segment:
                am = ANSWER_RE.match(_entry_text(entry))
                if am:
                    value = am.group(1).strip()
                    if value:
                        refs.append(html.escape(value))
                else:
                    stem_entries.append(entry)
            questions.append(_make_manual_candidate(
                stem_entries, '<br>'.join(refs) if refs else None,
                candidate_id=f's{section_index}q{len(questions)+1}', qtype='translation', score=score,
                material_html=prose_material, external_number=str(qidx + 1),
            ))

    if poem:
        poem_starts = [i for i, entry in enumerate(poem) if SUBQUESTION_RE.match(_entry_text(entry))]
        first_poem_q = poem_starts[0] if poem_starts else len(poem)
        poem_material = _join_html(poem[:first_poem_q])
        poem_instruction = _entry_text(poem[0]) if poem else ''
        poem_scores = _instruction_scores(poem_instruction, len(poem_starts))
        poem_questions = _parse_subjective_segments(
            poem[first_poem_q:], section_index=section_index, material_html=poem_material,
            scores=poem_scores, qtype='poetry', start_pattern=SUBQUESTION_RE,
        )
        for question in poem_questions:
            question['candidate_id'] = f's{section_index}q{len(questions)+1}'
            questions.append(question)
    return questions


def _parse_chinese_essay(entries: list[dict[str, Any]], *, section_index: int, score: float) -> list[dict[str, Any]]:
    ref_idx = next((i for i, entry in enumerate(entries) if REFERENCE_ESSAY_RE.match(_entry_text(entry))), len(entries))
    stem_entries = entries[:ref_idx]
    reference_entries = entries[ref_idx + 1:] if ref_idx < len(entries) else []
    return [_make_manual_candidate(
        stem_entries, _join_html(reference_entries), candidate_id=f's{section_index}q1',
        qtype='essay', score=score,
    )]


def _split_sections(lines: list[dict[str, Any]]) -> tuple[str, list[tuple[str, list[dict[str, Any]]]]]:
    title = _entry_text(lines[0]) if lines else '未命名试卷'
    sections: list[tuple[str, list[dict[str, Any]]]] = []
    current_title: str | None = None
    current: list[dict[str, Any]] = []
    for entry in lines[1:]:
        text = _entry_text(entry)
        if SECTION_RE.match(text):
            if current_title is not None:
                sections.append((current_title, current))
            current_title = text
            current = []
        elif current_title is not None:
            current.append(entry)
    if current_title is not None:
        sections.append((current_title, current))
    return title, sections


def map_document(ast: dict[str, Any], subject_code: str) -> dict[str, Any]:
    if subject_code not in {'chinese', 'math', 'english'}:
        raise ValueError('unsupported subject')
    lines = _document_lines(ast)
    title, raw_sections = _split_sections(lines)
    warnings: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []

    for sidx, (section_title, entries) in enumerate(raw_sections, start=1):
        default_score = _section_score(section_title) or 0.0
        score_sequence = _score_sequence(section_title)

        if subject_code == 'math':
            if '单选' in section_title:
                questions = _parse_standard_answer_section(
                    entries, qtype='single_choice', default_score=default_score,
                    score_sequence=score_sequence, section_index=sidx, warnings=warnings,
                )
            elif '填空' in section_title:
                questions = _parse_standard_answer_section(
                    entries, qtype='fill_blank', default_score=default_score,
                    score_sequence=score_sequence, section_index=sidx, warnings=warnings,
                )
            else:
                questions = _parse_standard_answer_section(
                    entries, qtype='solution', default_score=default_score,
                    score_sequence=score_sequence, section_index=sidx, warnings=warnings,
                )
        elif subject_code == 'english':
            if '语音' in section_title or '词汇' in section_title:
                entries = _explode_embedded_numbered_questions(entries)
                questions = _parse_standard_answer_section(
                    entries, qtype='single_choice', default_score=default_score,
                    score_sequence=score_sequence, section_index=sidx, warnings=warnings,
                )
            elif '完形' in section_title:
                questions = _parse_english_cloze(
                    entries, section_index=sidx, score=default_score, warnings=warnings,
                )
            elif '阅读理解' in section_title:
                questions = _parse_reading_choices(
                    entries, section_index=sidx, score=default_score, warnings=warnings, start_number=36,
                )
            elif '补全对话' in section_title:
                questions = _parse_english_completion(
                    entries, section_index=sidx, score=default_score, warnings=warnings,
                )
            elif '书面表达' in section_title:
                questions = _parse_english_essay(
                    entries, section_index=sidx, score=_standalone_score(section_title) or 20.0,
                )
            else:
                questions = []
                _make_warning(warnings, 'unknown_section', f'无法识别英语章节“{section_title}”。', severity='blocking')
        else:
            if '单项选择' in section_title:
                questions = _parse_standard_answer_section(
                    entries, qtype='single_choice', default_score=default_score,
                    score_sequence=score_sequence, section_index=sidx, warnings=warnings,
                )
            elif '现代文阅读' in section_title:
                questions = _parse_chinese_modern(entries, section_index=sidx, warnings=warnings)
            elif '古代诗文阅读' in section_title:
                questions = _parse_chinese_classical(entries, section_index=sidx, warnings=warnings)
            elif '写作' in section_title:
                questions = _parse_chinese_essay(
                    entries, section_index=sidx, score=_standalone_score(section_title) or 60.0,
                )
            else:
                questions = []
                _make_warning(warnings, 'unknown_section', f'无法识别语文章节“{section_title}”。', severity='blocking')

        sections.append({
            'title': section_title,
            'order_index': sidx,
            'instruction': None,
            'score_total': sum(float(q.get('score') or 0) for q in questions),
            'questions': questions,
        })

    if ast.get('unsupported_object_count'):
        _make_warning(warnings, 'unsupported_docx_object', 'DOCX 中含暂不支持的对象，请人工核对。', severity='blocking')

    return {
        'title': title,
        'subject_code': subject_code,
        'source_filename': ast.get('source_filename'),
        'source_sha256': ast.get('source_sha256'),
        'source_size': ast.get('source_size'),
        'media_count': ast.get('media_count', 0),
        'sections': sections,
        'warnings': warnings,
    }
