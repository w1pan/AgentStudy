# 轻衡

轻衡是一个单用户饮食记录与热量缺口原型，支持 Windows 本地运行、可信局域网访问，以及 Docker Compose 部署到阿里云 ECS。

大模型负责食物识别和建议表达；服务端负责热量计算、误差合成、数据校验与数据库事务。当前不提供登录、多用户隔离、点餐、菜谱或趋势图，不同设备访问同一服务时共享同一份数据。

## 主要功能

- **用户档案**：记录年龄、身高、体重、生理性别与目标，计算静息代谢和目标缺口。
- **饮食记录**：手动记录整餐，或上传照片识别食物与份量；支持手动餐食编辑和餐食删除。
- **运动与体重**：按活动和时长估算运动消耗，记录每日体重。
- **今日汇总**：展示摄入区间、预计消耗、热量缺口及目标区间状态。
- **历史记录**：按月份和日期查看记录；清空历史时保留档案当前值与内置目录。
- **AI 建议与追问**：按需生成今日建议，复用有效缓存，并支持 SSE 流式追问。
- **营养证据检索**：照片识别的热量密度置信度较低时，通过受限 ReAct Agent 按需联网寻找同类预制菜证据，合格后用于改善估算。

## 技术与目录

| 层级 | 技术与职责 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Pinia、Vite；页面交互、状态管理与 API 调用 |
| 后端 | FastAPI、Python、psycopg；参数校验、业务计算与 PostgreSQL 持久化 |
| AI | LangChain ChatOpenAI 接入 DashScope 兼容接口；create_agent 编排只读营养证据工具 |
| 部署 | PowerShell 本地启停；Docker Compose、Nginx 与 PostgreSQL 容器部署 |

```text
Agents/
├─ Agent/                 # Vue 前端及组件测试
├─ agent-learning/        # FastAPI、AI 调用、数据库迁移及后端测试
├─ deploy/ecs/            # ECS 打包脚本、Dockerfile、Compose 与 Nginx 配置
├─ docs/                  # 实现逻辑与部署进度
├─ .runtime/              # 本地 PostgreSQL、数据与运行日志（不提交）
├─ start-qingheng.ps1     # 本地一键启动
├─ stop-qingheng.ps1      # 本地停止服务
└─ enable-qingheng-lan.ps1 # 专用网络防火墙配置
```

## 本地准备

需要 PowerShell、Node.js（`^20.19.0 || >=22.12.0`）、npm、uv、Python 3.14 或更高版本，以及 PostgreSQL 17。AI 功能还需要可用的 DashScope API 密钥和模型权限。

### 1. 安装依赖

从仓库根目录执行：

```powershell
cd agent-learning
uv sync
cd ..\Agent
npm ci
cd ..
```

### 2. 配置后端

首次使用时复制配置模板，并填写数据库连接和模型密钥；已有 `.env` 时直接编辑，避免覆盖：

```powershell
Copy-Item .\agent-learning\.env.example .\agent-learning\.env
```

示例配置（模型名称与本地模板一致，可根据账户权限调整）：

```dotenv
DATABASE_URL=postgresql://agent_user:change-me@127.0.0.1:5432/agent_learning
DASHSCOPE_API_KEY=your_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen3.5-plus
ADVICE_MODEL=qwen3.5-plus
NUTRITION_REACT_ENABLED=true
NUTRITION_REACT_MODEL=qwen3.8-max-0902
NUTRITION_WEB_SEARCH_ENABLED=true
NUTRITION_SEARCH_MODEL=qwen3.8-max-0902
NUTRITION_SEARCH_STRATEGY=max
```

数据库及账号须提前创建，密码需替换为实际值；服务启动时自动执行迁移并初始化内置食物与 MET 活动目录。真实 `.env`、API 密钥与数据库文件不要提交到 Git。

设置 `NUTRITION_REACT_ENABLED=false` 可切回直接检索流程；设置 `NUTRITION_WEB_SEARCH_ENABLED=false` 可关闭营养联网检索；`NUTRITION_SEARCH_STRATEGY` 支持 `turbo` 和 `max`。

### 3. 选择启动方式

**一键启动**适用于已准备好仓库本地运行环境的 Windows 电脑。脚本使用 `.runtime/postgresql-17.10/pgsql/bin/` 下的 PostgreSQL 程序与 `.runtime/postgres-data/` 数据目录；这些运行文件不随 Git 仓库分发，脚本不会下载 PostgreSQL 或创建数据库账号。

```powershell
.\start-qingheng.ps1
```

启动后输出本机地址 `http://127.0.0.1:5173/` 和可用局域网地址。只允许当前电脑访问时执行：

```powershell
.\start-qingheng.ps1 -LocalOnly
```

**手动启动**适用于自行安装和管理 PostgreSQL 的环境。先启动数据库，再分别在两个终端运行：

```powershell
# 终端一：后端
cd agent-learning
uv run python -m app.main
```

```powershell
# 终端二：前端，仅监听本机
cd Agent
npm run dev -- --host 127.0.0.1
```

后端监听 `127.0.0.1:8001`，前端通过 Vite 的同源代理访问 `/api`。健康检查为 `http://127.0.0.1:8001/api/v1/health`，API 文档为 `http://127.0.0.1:8001/docs`。

### 4. 停止与局域网访问

一键启动窗口按 Ctrl+C 会停止它启动的前后端，PostgreSQL 保持运行。也可以从仓库根目录执行：

```powershell
.\stop-qingheng.ps1
# 同时关闭本地 PostgreSQL
.\stop-qingheng.ps1 -IncludeDatabase
```

局域网模式下，同一网络中的设备可访问启动脚本输出的 `http://局域网IP:5173/`；后端和数据库仍只监听本机。应用没有账户认证，只应在可信专用网络使用，不要将开发端口转发到公网。

如被 Windows 防火墙拦截，先将可信家庭或办公网络设为“专用网络”，再以管理员身份执行：

```powershell
.\enable-qingheng-lan.ps1
```

该脚本遇到公用网络会拒绝开放；规则限定专用网络、本地子网、Node 程序和 TCP 5173。

## ECS 部署

仓库提供 Ubuntu ECS 的 Docker Compose 部署方案。Windows 打包脚本先执行前端类型检查和生产构建，再打包前端产物、后端与部署配置；真实 `.env`、本机数据库和虚拟环境不包含在部署包内。

```powershell
.\deploy\ecs\package.ps1
```

默认访问链路：

```text
浏览器 127.0.0.1:18080 → SSH 隧道 → ECS 127.0.0.1:8080
  → Nginx → FastAPI → PostgreSQL
```

只有 Web 发布 ECS 本机端口，API 和数据库不发布宿主机端口。首次部署创建空数据库，不自动迁移本机记录；更新前应备份数据库并保留服务器现有 `.env`，不要执行会删除数据卷的 `docker compose down -v`。

完整的上传、配置、隧道、备份和更新步骤见 [ECS 部署指南](deploy/ecs/README.md)。本地与 ECS 配置模板的默认模型可能不同，应以各自实际环境配置为准。

## 数据与 AI 边界

- 上传图片经真实格式、帧数、像素与完整解码校验后，只在内存中重编码；识别后不保存原图或缩略图。重编码图片会发送至 DashScope，AI 建议与追问也会将所需业务上下文发送至模型服务。
- 视觉模型估算食物、份量和置信度，服务端结合模板与证据计算热量和整餐不确定度，不额外增加份量确认步骤。
- 受限 ReAct Agent 必须先检查现有证据，再按需调用联网工具；工具只读且每个最多调用一次。模型不能计算最终热量或写数据库，检索失败时回退原有证据与确定性流程。
- 预计消耗使用 Mifflin–St Jeor 静息代谢乘以 1.2，再加当天运动区间中点；运动记录自身仍保留估算区间。缺口区间由预计消耗与摄入上下限计算。

## 验证

从仓库根目录执行后端测试，再运行前端测试、类型检查和生产构建：

```powershell
cd agent-learning
uv run python -m unittest discover -s tests -v
cd ..\Agent
npm run test:unit -- --run
npm run type-check
npm run build
cd ..
```

这些命令用于代码验证；真实照片识别、模型权限和部署后的完整交互仍需在实际环境验收。

## 进一步阅读

- [项目实现逻辑](docs/项目实现逻辑.md)：架构、照片估算、受限 Agent、缓存与数据流程。
- [后端说明](agent-learning/README.md)：数据库初始化、图片校验、营养检索与建议生成。
- [ECS 部署指南](deploy/ecs/README.md)：容器部署、SSH 隧道、备份与常见问题。
- [部署进度记录](docs/部署进度-2026-09-20.md)：历史部署过程与待完成事项，以实际环境验收结果为准。
