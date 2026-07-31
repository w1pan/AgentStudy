# LangChain Agent 学习项目

## 项目结构

```
agent-learning/
├── README.md              # 本文件
├── requirements.txt        # Python 依赖
├── .env.example           # 环境变量模板
├── 01_simple_chain.py     # 最简单的 Chain
├── 02_with_tools.py       # 带工具的 Agent
├── 03_agent_loop.py       # 手动实现 Agent 循环
├── 04_with_memory.py      # 带记忆的 Agent
└── 05_rag_agent.py        # RAG + Agent
```

## 快速开始

### 1. 安装依赖

```bash
cd agent-learning
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API 密钥：

```
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here  # 仅 05_rag_agent.py 需要
```

### 3. 运行示例

```bash
python 01_simple_chain.py
python 02_with_tools.py
python 03_agent_loop.py
python 04_with_memory.py
python 05_rag_agent.py
```

## 学习顺序

| 阶段 | 文件 | 核心概念 |
|------|------|---------|
| Day 1 | 01_simple_chain.py | Prompt + LLM = Chain |
| Day 2 | 02_with_tools.py | Tool Use / ReAct |
| Day 3 | 03_agent_loop.py | 完整 Agent 循环原理 |
| Day 4 | 04_with_memory.py | Memory 管理 |
| Day 5+ | 05_rag_agent.py | RAG 检索增强 |

## 核心概念

### Chain
```
User → Prompt Template → LLM → Output
```

### Agent 循环
```
User Input → LLM → stop_reason?
                    ├── end_turn → Return Final Answer
                    └── tool_use → Execute Tool → Feed Result to LLM → Loop
```

### RAG
```
Query → Retriever → Relevant Docs → LLM → Answer
```

## 环境要求

- Python 3.10+
- Anthropic API Key（必须）
- OpenAI API Key（仅 RAG 示例）

## 扩展练习

每个文件末尾都有"扩展练习"建议，尝试完成它们以加深理解。