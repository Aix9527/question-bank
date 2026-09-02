# 专科复习在线题库系统设计规格

日期：2026-09-02
版本：Design v1.0

## 1. 项目目标

建立一套可长期反复使用、可持续扩充的在线题库系统。语文、数学、英语分别建立独立题库，但共用账号、做题记录、成绩、错题、收藏、批改和管理后台。

首批资料来自《专科复习资料.rar》中的 6 套 DOCX：

- 数学：
  - 成考高起专数学（文）模拟题一.docx
  - 成考高起专、高起本数学（文）模拟题二.docx
- 英语：
  - 成考高起专英语-考前模拟题1.docx
  - 成考高起专英语-考前模拟题2.docx
- 语文：
  - 成考高起专语文 模拟1.docx
  - 成考高起专语文 模拟2.docx

## 2. 第一阶段范围

### 2.1 必做

1. 语文 / 数学 / 英语三科独立入口。
2. 试卷中心。
3. 顺序练习。
4. 随机练习。
5. 模拟考试。
6. 自动保存答案。
7. 客观题自动判分。
8. 主观题人工批复入口。
9. 可选 AI 辅助批改接口预留。
10. 答案与解析。
11. 错题本。
12. 错题重练。
13. 收藏题。
14. 成绩历史。
15. 科目 / 题型 / 知识点正确率统计。
16. 管理后台题目增删改查。
17. DOCX 试卷导入与人工校验流程。
18. 数据导出与备份。

### 2.2 第一阶段不做

- 付费会员
- 班级排名
- 直播课堂
- 社交功能
- 自动发布
- 复杂机构权限

## 3. 信息架构

### 3.1 首页

- 语文题库
- 数学题库
- 英语题库
- 今日练习
- 最近成绩
- 待复习错题
- 继续上次练习

### 3.2 科目页

每科统一提供：

- 开始刷题
- 模拟考试
- 试卷中心
- 专项练习
- 错题本
- 收藏题
- 成绩记录
- 学习分析

### 3.3 管理后台

- 科目管理
- 试卷管理
- 题目管理
- DOCX 导入
- 导入审核
- 批改中心
- 成绩查看
- 数据备份

## 4. 三科题型模型

### 4.1 语文

支持：

- 单选题
- 多选题
- 填空题
- 文言文材料题
- 古诗词题
- 现代文阅读
- 简答题
- 作文

判分：

- 单选 / 多选：自动判分。
- 填空：支持标准答案、多个可接受答案、人工复核。
- 阅读 / 简答：默认人工批复；预留 AI 建议分、得分点分析。
- 作文：默认人工批复；预留 AI 从立意、内容、结构、语言、错别字等维度建议评分。

### 4.2 数学

支持：

- 单选题
- 多选题
- 填空题
- 判断题
- 计算题
- 解答题
- 综合题

判分：

- 客观题：自动。
- 数值型填空：允许精确值、等价值、误差范围等判定模式。
- 解答题：人工批复；预留步骤评分、公式/表达式识别接口。

### 4.3 英语

支持：

- 语音知识
- 词汇语法
- 单项选择
- 完形填空
- 阅读理解
- 补全对话
- 翻译
- 写作

判分：

- 客观题：自动。
- 翻译：人工批复；预留 AI 参考评分。
- 写作：人工批复；预留 AI 在内容、语法、词汇、结构、表达等维度给出建议。

## 5. 核心数据模型

### 5.1 Subject

- id
- code: chinese | math | english
- name
- enabled

### 5.2 Paper

- id
- subject_id
- title
- source_file
- paper_type: mock | past | custom
- total_score
- time_limit_minutes
- status: draft | published | archived
- version
- created_at
- updated_at

### 5.3 PaperSection

- id
- paper_id
- title
- order_index
- instruction
- score_total

### 5.4 Question

- id
- subject_id
- type
- stem_html
- material_html
- answer_mode
- standard_answer_json
- explanation_html
- score
- difficulty
- knowledge_points
- source
- status
- version

题干、材料和解析使用安全 HTML / 富文本表示，允许数学公式、图片、上下标、表格等。

### 5.5 QuestionOption

- id
- question_id
- label
- content_html
- order_index

### 5.6 PaperQuestion

连接 Paper 与 Question：

- paper_id
- question_id
- section_id
- order_index
- score_override

这样同一道题可被多套试卷复用。

### 5.7 Attempt

一次刷题或考试会话：

- id
- user_id
- subject_id
- paper_id nullable
- mode: practice | exam | wrong_review | random
- status: in_progress | submitted | graded
- started_at
- submitted_at
- score
- max_score

### 5.8 AnswerRecord

- attempt_id
- question_id
- answer_json
- is_correct nullable
- auto_score nullable
- final_score nullable
- grading_status: auto | pending_manual | reviewed
- time_spent_seconds
- answered_at

### 5.9 ManualReview

- answer_record_id
- reviewer_id
- suggested_score nullable
- final_score
- comment
- rubric_json
- reviewed_at

### 5.10 WrongQuestion

- user_id
- question_id
- wrong_count
- correct_review_count
- mastery_status: pending | learning | mastered
- last_wrong_reason
- next_review_at nullable

### 5.11 Favorite

- user_id
- question_id
- created_at

## 6. 答题模式

### 6.1 练习模式

每题提交后：

1. 客观题立即判分。
2. 显示正确答案。
3. 显示解析。
4. 可收藏。
5. 错题自动进入错题本。
6. 用户可标记错误原因。
7. 可继续下一题。

### 6.2 模拟考试

- 倒计时。
- 自动保存。
- 不即时显示答案与解析。
- 支持标记疑问。
- 提交后统一计算客观题成绩。
- 主观题进入待批复。
- 最终成绩在人工批改完成后更新。

### 6.3 错题重练

优先顺序：

1. 重复错题。
2. 最近错题。
3. 长时间未复习题。

连续多次答对后转为“已掌握”，但历史不删除。

## 7. 错误原因

### 数学

- 不会
- 公式忘记
- 思路错误
- 计算错误
- 审题错误
- 粗心

### 英语

- 单词不认识
- 语法不会
- 句子没看懂
- 阅读判断错误
- 粗心

### 语文

- 知识点不会
- 审题错误
- 阅读理解偏差
- 得分点不完整
- 表达问题
- 粗心

## 8. DOCX 导入管线

导入采取“自动解析 + 人工校验 + 发布”三阶段，禁止解析完成后直接进入正式题库。

### 8.1 上传

管理员上传 DOCX，选择或自动识别：

- 科目
- 试卷名称
- 考试时长
- 总分

### 8.2 Parser 层

只负责提取文档结构，不做业务推断：

- 段落
- 表格
- 图片
- 编号
- 样式
- 加粗/下划线
- 数学公式或嵌入对象（在能力范围内保留）

输出统一中间格式 Document AST。

### 8.3 Mapper 层

根据科目规则识别：

- 大题标题
- 小题编号
- 题干
- A/B/C/D 选项
- 材料块
- 分值
- 答案区
- 解析区

不得悄悄丢弃不能识别的内容。所有不确定项进入 warnings。

### 8.4 Review 层

后台显示原文与解析结果对照：

- 题目切分是否正确
- 选项是否正确
- 正确答案
- 分值
- 题型
- 知识点
- 图片/公式是否完整

管理员确认后才能发布。

### 8.5 导入幂等

每次上传计算 SHA-256：

- 同文件重复导入时给出提示。
- 已发布试卷修改后生成新版本，不静默覆盖历史答题数据。

## 9. 首批 6 套卷的落库规则

建立：

### 语文

- Paper: 语文模拟卷 1
- Paper: 语文模拟卷 2

### 数学

- Paper: 数学（文）模拟卷 1
- Paper: 数学（文）模拟卷 2

### 英语

- Paper: 英语考前模拟卷 1
- Paper: 英语考前模拟卷 2

导入时保留原始文件名作为 source_file，不把原始 DOCX 作为运行时题库。

如果 DOCX 中答案与试题分离，则导入器需在同一文件内建立题号匹配；无法可靠匹配的题目标记 pending_review，不允许自动发布。

## 10. 判分规则

### 10.1 单选

标准答案完全匹配即得满分，否则 0 分。

### 10.2 多选

第一版采用配置化策略：

- exact_only：完全匹配才得分。
- partial：少选部分得分、错选 0 分。

默认以试卷规则为准；无法判断时导入审核必须人工选择。

### 10.3 填空

支持：

- exact_text
- normalized_text
- numeric_exact
- numeric_tolerance
- multiple_acceptable
- manual

### 10.4 主观题

任何 AI 评分都只能作为 suggested_score，最终分数存 final_score，且保留人工覆盖能力。

## 11. 学习统计

至少展示：

- 每科总做题数
- 每科正确率
- 最近 7 / 30 天练习量
- 模拟卷成绩趋势
- 各题型正确率
- 各知识点正确率
- 错题数量
- 已掌握错题数量
- 重复错误题

## 12. 权限模型

第一版只设：

### Learner

- 做题
- 看自己的成绩
- 错题
- 收藏
- 查看已开放的答案解析

### Admin / Reviewer

- 导入试卷
- 编辑题目
- 发布/下架试卷
- 批改主观题
- 查看成绩
- 数据备份

如果后续多人教学，再拆分 Teacher / Student / Class。

## 13. 推荐技术架构

### Web

- Next.js / React
- TypeScript
- 响应式设计：电脑优先，同时兼容手机

### API

- FastAPI
- Pydantic
- SQLAlchemy

### Database

开发 / 单机阶段：SQLite。

在线多人阶段：PostgreSQL。

业务层不得依赖 SQLite 特有行为，确保可迁移。

### Storage

- 原始 DOCX
- 题目图片
- 作答图片
- 后续手写答案附件

使用统一 StoragePort；本地模式用磁盘，公网模式可切 S3 兼容对象存储。

## 14. API 边界

示例：

- GET /api/subjects
- GET /api/subjects/{subject}/papers
- GET /api/papers/{id}
- POST /api/attempts
- PATCH /api/attempts/{id}/answers/{question_id}
- POST /api/attempts/{id}/submit
- GET /api/me/wrong-questions
- POST /api/questions/{id}/favorite
- GET /api/me/statistics
- POST /api/admin/imports/docx
- GET /api/admin/imports/{id}/review
- POST /api/admin/imports/{id}/publish
- GET /api/admin/reviews/pending
- POST /api/admin/reviews/{answer_id}

## 15. 关键可靠性要求

1. 每次答案变更立即自动保存。
2. 刷新页面可恢复进行中的答题会话。
3. 提交试卷必须幂等，重复点击不能重复产生考试记录。
4. 历史答题绑定 Question 版本，后续改题不篡改历史。
5. 导入器 fail-closed：识别不确定时进入审核，不猜测发布。
6. 原始文件、导入 AST、发布后题库记录之间保存追溯关系。
7. 数据库每日可备份；支持 JSON/CSV 导出学习记录。

## 16. 测试要求

### Unit

- 客观题评分
- 填空归一化
- 多选规则
- 错题状态变化
- 试卷计分
- DOCX 编号与选项识别

### Integration

- 创建练习 → 作答 → 自动保存 → 提交 → 成绩
- 考试 → 客观评分 → 主观待批 → 人工批复 → 最终成绩
- DOCX 上传 → 解析 → 审核 → 发布

### E2E

每科至少覆盖：

- 进入科目
- 打开试卷
- 完成若干题
- 刷新恢复
- 提交
- 查看结果
- 错题重练

## 17. 第一阶段验收标准

1. 三科入口明确独立。
2. 6 套卷均可在后台看到并完成审核流程。
3. 客观题可以在线作答并准确自动判分。
4. 主观题进入待批复列表并可人工给分/评语。
5. 答题中刷新不会丢失已保存答案。
6. 模拟卷可重复作答，历史成绩彼此独立。
7. 错题自动沉淀，可重复练习。
8. 收藏题可单独练习。
9. 首页能看到三科最近成绩和待复习错题。
10. 管理员能新增、修改、下架题目和试卷。
11. 后续新 DOCX 可沿同一导入流程继续扩充题库。

## 18. 实施顺序建议

M1：基础工程 + 数据库 + 三科导航

M2：题库 / 试卷 / 答题核心

M3：自动评分 + 提交 + 成绩历史

M4：错题 / 收藏 / 统计

M5：主观题批改中心

M6：DOCX 导入器 + 审核后台

M7：首批 6 套卷导入与校验

M8：公网部署、备份与安全加固

## 19. 后续扩展（不纳入 v1 必须项）

- AI 作文批改
- AI 英语写作批改
- AI 数学步骤分析
- 拍照上传手写答案
- 错题间隔复习算法
- 同类题推荐
- AI 生成同知识点练习
- 班级 / 教师 / 学生
- 微信登录
- 小程序客户端
