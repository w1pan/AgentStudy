# 轻衡

“轻衡”是一个可在本机或可信局域网内运行的单用户饮食与热量缺口原型。它包含用户档案、整餐饮食记录、运动与每日体重、今日缺口、按日期历史和按需 AI 建议，不提供点餐、菜谱、趋势图或多人账户。

## 目录

```text
Agents/
├─ Agent/                 # Vue 3 + Pinia + Vite
├─ agent-learning/        # FastAPI + psycopg + DashScope
├─ .runtime/              # 本地 PostgreSQL 与运行日志（不提交）
└─ start-qingheng.ps1     # 一键启动入口
```

## 首次准备

1. 在 `agent-learning/.env` 中配置：

```dotenv
DATABASE_URL=postgresql://agent_user:password@127.0.0.1:5432/agent_learning
DASHSCOPE_API_KEY=your_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen3.5-plus
ADVICE_MODEL=qwen3.5-plus
```

2. 安装依赖：

```powershell
cd agent-learning
uv sync
cd ..\Agent
npm install
```

3. 从仓库根目录启动：

```powershell
.\start-qingheng.ps1
```

启动后会同时打印本机地址和可用的局域网地址，例如 `http://192.168.1.20:5173/`。同一 Wi-Fi 或有线局域网中的设备可打开该地址。FastAPI 和 PostgreSQL 仍只监听 `127.0.0.1`，局域网请求通过 Vite 的同源代理访问 API。

如只允许当前电脑访问，可使用：

```powershell
.\start-qingheng.ps1 -LocalOnly
```

局域网模式没有账户认证，只应在可信的专用网络使用，不要将端口转发到公网。若 Windows 防火墙拦截：先确认这是可信家庭/办公网络并在 Windows 设置中将它标记为“专用网络”，然后以管理员身份运行：

```powershell
.\enable-qingheng-lan.ps1
```

该脚本遇到公用网络会拒绝开放；创建的规则只允许专用网络、本地子网、Node 程序和 TCP 5173。后端 8001 与数据库 5432 始终不会对局域网监听。

## 验证

```powershell
cd agent-learning
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

cd ..\Agent
npm run test:unit -- --run
npm run type-check
npm run build
```

图片只在内存中验证与重编码，识别后不保存原图或缩略图。视觉模型只估食物、份量和置信度，模板热量、合理份量边界及整餐不确定度均由服务端计算；不会增加份量确认步骤。预计消耗使用 Mifflin–St Jeor × 1.2 加当天运动区间中点的固定值，运动记录本身仍保留独立估算区间。历史清空保留档案当前值和内置食物/MET 目录。
