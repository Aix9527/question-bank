# 专科复习在线题库 v0.5

> **v0.5 Final（Production Ready）**：本地 Windows 端到端验收通过（后端 60/60、前端生产构建成功、learner/admin 权限隔离、管理后台六大模块）。此版本已封版，后续新需求请基于 git tag `v0.5-final` 另开 v0.6 分支，不再修改本版本。

语文、数学、英语三个独立题库，共用在线答题、自动判分、错题复练、收藏、成绩历史、学习统计、DOCX 导入、主观题批改和管理后台。v0.5 在 v0.4 基础上加入简单多用户登录、学习者/管理员权限分离、知识点精细化、可选 AI 主观题建议分，以及可直接上 HTTPS 的生产部署基线。

## v0.5 重点

- **简单用户系统**：数据库用户 + PBKDF2-HMAC-SHA256 密码哈希 + 随机 Bearer Session；支持 learner / admin 两种角色。
- **学习数据隔离**：attempt、错题、收藏、历史、统计均按登录用户隔离；跨用户读取 attempt 返回 404。
- **v0.4 无损升级**：旧单用户数据使用 `user_id=1`。首次开启登录并配置 bootstrap admin 时，会把 `id=1/local` 原地升级为首个管理员，因此旧学习历史不会丢失。
- **浏览器安全会话**：后端 token 仅保存在 Next.js HttpOnly Cookie 中；浏览器客户端通过同源 learner/admin proxy 访问 API。
- **知识点精细化**：DOCX 新发布题目自动按三科规则打知识点；已有手工标签优先；提供 dry-run/apply 批量补标脚本。
- **AI 主观题建议分**：可选 OpenAI Responses API Structured Outputs；AI 只能产生 `suggested_score`、评语、优点、改进点和 rubric，**绝不写 `final_score`**；最终成绩必须管理员人工确认。
- **部署加固**：健康检查、管理员创建/重置脚本、SQLite 恢复脚本、普通 Compose 和 Caddy HTTPS 生产 Compose。
- **备份导出增强**：JSON/CSV 导出包含用户公开元数据和 AI 建议记录，但不导出 password hash、session token/hash。
- **多人安全清理**：清理脚本默认只清 `user_id=1`；全用户清理必须显式 `--all-users`。

## 首批真实卷

| 科目 | 试卷 | 题数 | 总分 | 媒体对象 |
|---|---|---:|---:|---:|
| 语文 | 语文模拟卷1 | 20 | 150 | 0 |
| 语文 | 语文模拟卷2 | 20 | 150 | 0 |
| 数学 | 数学（文）模拟卷1 | 18 | 150 | 6 |
| 数学 | 数学（文）模拟卷2 | 18 | 150 | 15 |
| 英语 | 英语考前模拟卷1 | 56 | 150 | 0 |
| 英语 | 英语考前模拟卷2 | 56 | 150 | 0 |

共 **6 卷 / 188 题 / 667 个选项 / 900 分**。首批 188/188 题可通过 v0.5 规则获得知识点。英语卷 2 原资料第 4、5 题答案/解析冲突的人工审核记录继续保存在 `data/initial-review-decisions.json`。

## 目录

- `apps/api` FastAPI 后端
- `apps/web` Next.js 前端
- `data/source_papers` 6 套原始 DOCX
- `scripts/import_initial_papers.py` 首批真实卷 SHA-256 幂等导入
- `scripts/enrich_knowledge_points.py` 已有题库知识点 dry-run/apply
- `scripts/create_admin.py` 创建/重置管理员
- `scripts/backup_db.py` SQLite 一致性备份
- `scripts/restore_db.py` 带 integrity check 与预恢复备份的 SQLite 恢复
- `scripts/healthcheck.py` API ready 检查
- `docker-compose.yml` 本机/内网部署
- `docker-compose.prod.yml` Caddy HTTPS 生产部署
- `deploy/Caddyfile` 生产反向代理/TLS

## 1. Windows 本地使用：保持 v0.4 无登录体验

如果仍只给自己使用，不设置 `QUESTION_BANK_AUTH_REQUIRED=true` 即可保持 v0.4 行为，系统自动使用 `user_id=1`。

后端：

```powershell
cd apps\api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd apps\web
npm install
npm run dev
```

打开 `http://127.0.0.1:3000`。

## 2. Windows 本地测试多人登录

先指定同一个 SQLite 数据库，再启用认证：

```powershell
$env:QUESTION_BANK_DATABASE_URL="sqlite:///D:/question-bank/question_bank.db"
$env:QUESTION_BANK_AUTH_REQUIRED="true"
$env:QUESTION_BANK_BOOTSTRAP_ADMIN_USERNAME="admin"
$env:QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD="请替换成至少8位强密码"
```

然后启动后端/前端。浏览器进入 `/login` 登录。

> v0.4 升级注意：如果数据库中还没有 users 表，v0.5 会自动建表。原有 `user_id=1` 的学习记录不会迁移或复制，而是让首个 bootstrap 管理员直接继承 ID=1。

管理员页面：

- `/admin/users` 用户与角色
- `/admin/papers` 试卷管理
- `/admin/questions` 题目管理
- `/admin/imports` DOCX 导入审核
- `/admin/reviews` 主观题人工/AI 辅助批改
- `/admin/backup` 备份与导出

## 3. 首批 6 套真实卷导入

正式按已审阅修正发布：

```powershell
python scripts\import_initial_papers.py --mode publish-reviewed
```

只进入审核队列：

```powershell
python scripts\import_initial_papers.py --mode review
```

导入按原始 DOCX SHA-256 幂等，重复运行不会重复建卷。

## 4. 知识点精细化

先查看会修改什么：

```powershell
python scripts\enrich_knowledge_points.py
```

写入缺失标签：

```powershell
python scripts\enrich_knowledge_points.py --apply
```

只有明确传入 `--overwrite` 才会覆盖已有人工知识点：

```powershell
python scripts\enrich_knowledge_points.py --apply --overwrite
```

## 5. AI 主观题建议分（可选）

默认关闭，完全人工批改仍可正常使用。要启用 OpenAI 建议分：

```powershell
$env:QUESTION_BANK_AI_PROVIDER="openai"
$env:OPENAI_API_KEY="你的 API Key"
$env:QUESTION_BANK_AI_MODEL="gpt-5.6-luna"
```

后台 `/admin/reviews` 点击“生成/刷新 AI 建议”。系统保存建议版本、建议分、置信度、评语、优点、改进点与 rubric；**AI 结果不会自动成为最终分数**。管理员必须在表单中确认/修改 `final_score` 后才能完成批复。

API：

```text
POST /api/admin/reviews/{answer_id}/ai-suggest
```

未配置 AI 时返回 503，不影响人工批改。

## 6. 用户与管理员

首次部署使用环境变量 bootstrap 管理员。之后可在 `/admin/users` 创建 learner/admin、停用账号或重设密码。

CLI 也可创建/重置管理员：

```powershell
python scripts\create_admin.py --username admin
```

脚本会交互式读取密码，避免把密码写进命令历史（也支持脚本提供的显式参数，详见 `-h`）。

登录 API：

```text
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/logout
```

启用 `QUESTION_BANK_AUTH_REQUIRED=true` 后，所有学习者私有 API 要求登录，所有 `/api/admin/*` 额外要求 admin 角色。

## 7. 备份、导出与恢复

备份：

```powershell
python scripts\backup_db.py
```

恢复前先检查帮助，并显式指定源备份与目标：

```powershell
python scripts\restore_db.py -h
```

恢复器会先执行 SQLite `PRAGMA integrity_check`，目标存在时默认拒绝覆盖；使用 `--force` 时先为当前目标创建 pre-restore 备份再替换。

网页 `/admin/backup` 仍支持：

- SQLite 一致性 `.db`
- 完整 JSON
- 多表 CSV ZIP + manifest

导出不会包含密码哈希和登录 Session。

## 8. 学习数据清理（v0.5 多人安全语义）

默认只清理 `user_id=1`：

```powershell
python scripts\reset_learner_data.py
```

指定学习账号：

```powershell
python scripts\reset_learner_data.py --user-id 2
```

清理全部用户（危险，必须显式）：

```powershell
python scripts\reset_learner_data.py --all-users
```

`clean_attempts.py` 使用同样的 `--user-id / --all-users` 语义，但保留收藏。

## 9. Docker Compose：本机/内网

```bash
cp .env.example .env
```

至少修改：

```text
QUESTION_BANK_BOOTSTRAP_ADMIN_PASSWORD=一个长且唯一的密码
```

然后：

```bash
docker compose config
docker compose up -d --build
```

- Web：`http://127.0.0.1:3000`
- API：`http://127.0.0.1:8000`
- Ready：`http://127.0.0.1:8000/api/health/ready`
- SQLite 持久卷：`question_bank_data`

此 compose 适合本机、可信内网或外部已有 HTTPS 反代的环境。

## 10. 正式公网部署：Caddy HTTPS

复制：

```bash
cp .env.production.example .env.production
```

设置真实域名、管理员强密码，按需设置 AI Key，然后：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

生产 Compose 的设计边界：

- 只对外开放 Caddy `80/443`
- FastAPI 不发布宿主机 8000 端口
- Web 与 API 仅走 Docker 内网
- 登录 Cookie 强制 `Secure`
- Caddy 自动申请/续期 TLS，并添加 HSTS / nosniff / Referrer-Policy
- 数据库仍是**单实例 SQLite**；适合个人/家庭/小班使用。若未来需要多实例、高并发或机构级多人并发，再迁 PostgreSQL。

## 11. 健康检查

```text
GET /api/health/live
GET /api/health/ready
```

CLI：

```powershell
python scripts\healthcheck.py --url http://127.0.0.1:8000/api/health/ready
```

## 12. 答案契约继续保持 v0.4 收敛策略

规范新数据：

```json
{"value": "B"}
```

旧 v0.3 数据：

```json
{"answer": "B"}
```

评分器读取顺序为 `value → answer(仅兼容旧数据)`；所有新导入、新建和人工修正只写 `value`。

## 验证

后端：

```powershell
pytest apps\api\tests -q
```

前端：

```powershell
cd apps\web
npm install
npm run build
```

普通 Docker：

```bash
docker compose config
```

生产 Docker：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config
```
