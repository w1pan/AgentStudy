"""
================================================================================
02_with_tools.py - 带工具调用的 Agent
================================================================================

目标：理解 Tool Use 机制，学会让 Agent 调用外部工具

这个例子展示：
1. 如何定义一个 Tool（工具）
2. 如何让 Agent 绑定工具并自动选择调用
3. 使用 LangChain Expression Language (LCEL) 构建 Agent

运行：python 02_with_tools.py
================================================================================

注意：本版本适用于 LangChain 1.x
================================================================================
"""

import os
from turtle import mode
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("❌ 请先设置 OPENAI_API_KEY 环境变量")
    exit(1)

# 1. 创建 LLM 实例
# llm = ChatAnthropic(model="claude-sonnet-4-6-20250514")

# 2. 定义工具函数（使用 @tool 装饰器）
@tool
def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前时间

    Args:
        format: 时间格式，默认为 "年-月-日 时:分:秒"
    """
    from datetime import datetime
    return datetime.now().strftime(format)

@tool
def calculate(expression: str) -> str:
    """计算数学表达式

    Args:
        expression: 数学表达式，如 "2 + 2" 或 "10 * 5"
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

# 3. 收集所有工具
# tools = [get_current_time, calculate]

# 4. 绑定工具到 LLM
#    bind_tools 让模型能够根据输入决定是否调用工具
# llm_with_tools = llm.bind_tools(tools)
model = ChatOpenAI(
    model="moonshot-v1-8k",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

agent = create_agent(model=model, tools=[get_current_time])

response = agent.invoke({
    "messages": [
        SystemMessage(content="你是一个时间助手，请回答用户的问题。"),
        HumanMessage(content="你使用的是什么模型"),
        AIMessage(content="我是时间助手，请问我有什么可以帮你的吗？"),
        HumanMessage(content="现在几点了？"),
    ]
})
for message in response["messages"]:
    message.pretty_print()
# 5. 创建 Agent 循环
# def agent_execute(question: str, verbose: bool = True) -> str:
#     """简单的 Agent 执行器：模型决定是否调用工具"""

#     messages = [HumanMessage(content=question)]

#     # 第一次调用：让模型决定是否调用工具
#     response = llm_with_tools.invoke(messages)

#     # 如果模型返回了工具调用
#     if hasattr(response, 'tool_calls') and response.tool_calls:
#         if verbose:
#             print(f"[思考] {response.content or '决定调用工具...'}")
#             print(f"[工具调用] {response.tool_calls}")

#         messages.append(response)

#         # 执行工具调用
#         for tool_call in response.tool_calls:
#             tool_name = tool_call['name']
#             tool_args = tool_call['args']
#             tool_id = tool_call['id']

#             # 找到对应的工具
#             for t in tools:
#                 if t.name == tool_name:
#                     result = t.invoke(tool_args)
#                     if verbose:
#                         print(f"[工具结果] {result}")

#                     # 将工具结果添加回消息
#                     from langchain_core.messages import ToolMessage
#                     messages.append(ToolMessage(
#                         tool_call_id=tool_id,
#                         name=tool_name,
#                         content=str(result)
#                     ))
#                     break

#         # 第二次调用：用工具结果生成最终回答
#         final_response = llm.invoke(messages)
#         return final_response.content

#     # 如果模型没有调用工具，直接返回回答
#     return response.content


# # 运行测试
# if __name__ == "__main__":
#     print("=" * 60)
#     print("02_with_tools.py - 带工具的 Agent")
#     print("=" * 60)

#     # 测试问题1：需要调用 get_time 工具
#     question1 = "现在几点了？请用24小时制表示。"

#     print(f"\n📝 问题1: {question1}\n")
#     result1 = agent_execute(question1)
#     print(f"\n📤 答案: {result1}")

#     # 测试问题2：需要调用 calculator 工具
#     question2 = "请帮我计算: (12 + 8) * 3 = ?"

#     print(f"\n{'=' * 60}")
#     print(f"\n📝 问题2: {question2}\n")
#     result2 = agent_execute(question2)
#     print(f"\n📤 答案: {result2}")

#     # 测试问题3：不需要调用工具
#     question3 = "你好，请介绍一下你自己"

#     print(f"\n{'=' * 60}")
#     print(f"\n📝 问题3: {question3}\n")
#     result3 = agent_execute(question3)
#     print(f"\n📤 答案: {result3}")

    # """
    # 扩展练习：
    # 1. 添加一个新工具，如搜索 Wikipedia 或查询天气
    # 2. 修改工具的 description，看看对结果的影响
    # 3. 尝试让 Agent 连续调用多个工具
    # """
