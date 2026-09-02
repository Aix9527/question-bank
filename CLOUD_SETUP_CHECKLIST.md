# v0.6-cloud 云端操作清单（用户本人执行）

> 配合 ChatGPT 对话 https://chatgpt.com/c/6a989ba8-213c-83e8-a6e3-46b6b9b4c167
> 本地代码改造已完成：v0.6-cloud 分支（提交 b297d13 / ef7827d），pytest 60/60，前端 build 通过。
> 以下云端步骤涉及注册/密码/授权，必须由你本人在浏览器完成；完成后把关键结果告诉本地助手回传 GPT。

---

## 阶段 2A：GitHub 建仓（最优先）

1. 登录 https://github.com （无账号先注册）
2. 右上角 `+` → **New repository**
3. 填写：
   - Repository name: `question-bank`
   - Visibility: **Private**
   - **不要勾选** Add README / Add .gitignore / Add license（本地已是完整 Git 仓库）
4. 点 **Create repository**
5. 把结果（GitHub 用户名 + 仓库地址 https://github.com/<你的用户名>/question-bank）告诉本地助手

> 之后本地执行推送由助手协助：`git remote add origin ...` → push main / v0.6-cloud / v0.5-final 标签。

---

## 阶段 2B：Supabase 建项目（拿两条连接串）

1. 登录 https://supabase.com （可用 GitHub 账号授权登录）
2. **New project**：
   - Name: `question-bank`
   - Database Password: **生成强密码**，自己保存（不要发给任何人/不回传对话）
   - Region: 靠近主要用户的区域；国内自用可选手动选择附近区域（如新加坡等）
   - 若看到类似 "Automatically expose new tables / Data API" 的选项：**不要开启**（本项目走 FastAPI → PostgreSQL，不需要 Supabase Data API 直接暴露表）
3. 项目创建后进入 **Project Settings → Database → Connection string**，保存两条：
   - **Transaction pooler（端口 6543）** → 用于 Vercel 生产 `DATABASE_URL`
   - **Session pooler（端口 5432）** → 用于迁移 `DATABASE_MIGRATION_URL`（首选；若 IPv4 直连受限再试 Direct Connection）
4. URL 格式示例（密码含 @ : / # % ? 等需 URL 编码）：
   - `postgresql+psycopg2://postgres.<ref>:<密码>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require`（6543 运行时）
   - `postgresql+psycopg2://postgres.<ref>:<密码>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require`（5432 迁移）

> 两条 URL 都**不要**发到对话里（含密码）；本地助手只需在配置时临时使用，随后清除。Supabase 自带 auth/storage/extensions 等 schema 与我们的 public 应用表不冲突，无需理会。

---

## 阶段 2C：Supabase Storage 建桶

1. 同一项目左侧 **Storage → New bucket**
2. Bucket name: `question-bank`
3. Public bucket: **OFF（保持 Private）**
4. 创建即可，暂不上传任何文件

---

## ⛔ 阶段 2D：暂不创建 Vercel Project

按 GPT 硬性 Gate：先完成 Schema Gate（Alembic baseline）+ Data Gate（SQLite→PG 迁移校验）之后，才创建 Vercel API/Web 两个 Project。**现在不要建。**

---

## 当前不做的事（防误操作）

- 不要把数据库密码、service_role key 发到任何对话
- 不要删除本地 v0.5 Final 数据 / release 备份
- 不要在 Supabase 里手改表结构
- 不要执行任何 Alembic / 迁移命令（等本地助手与 GPT 确认后执行）

---

## 方案说明（GPT 已批准）

- 本机**无 Docker**，baseline 生成采用**方案 A**：Supabase 项目建好后，用 Session Pooler（:5432）连接空库直接执行 `alembic revision --autogenerate`（只生成文件、不改库），文件交由 GPT 审计通过后再 `alembic upgrade head`。
- Storage bucket 可先于 baseline 创建（其元数据在 storage schema，与应用表不冲突）。
- baseline 生成前的硬门槛：public schema 中不得存在 15 张应用表（APP COLLISIONS = []）。
