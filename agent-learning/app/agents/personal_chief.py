import os
import sqlite3
from typing import List, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessageChunk
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_tavily import TavilySearch

from app.common.logger import logger
from app.rag.retriever import retrieve_recipes, RecipeSearchResult


# 加载环境变量
load_dotenv()
if not os.getenv("DASHSCOPE_API_KEY"):
    print("❌ 请先设置 DASHSCOPE_API_KEY 环境变量")
    exit(1)

# 加载模型
model = init_chat_model(
    model="qwen3.5-plus",
    model_provider="openai",
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

# web搜索工具使用tavily，作为RAG知识库不够时的补充
tavily = TavilySearch(max_results=2, topic="general")


# 记忆管理
checkpointer = SqliteSaver(sqlite3.connect("db/personal_chief.db", check_same_thread=False))
checkpointer.setup()


BASE_SYSTEM_PROMPT = """你是一名私人厨师。收到用户提供的食材照片或清单后，请按以下流程操作：
1. 识别和评估食材：若用户提供照片，首先辨识所有可见食材。基于食材的外观状态，评估其新鲜度与可用量。整理出一份“当前可用食材清单”。
2. 智能食谱检索：优先参考下面提供的“知识库检索结果”，这些都是经过筛选的高质量菜谱。如果知识库结果不足以回答用户需求，再调用 web_search 工具搜索互联网补充。
3. 多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分排序。制作简单且营养丰富的排名靠前。
4. 结构化方案输出：把排序后的食谱整理为一份结构清晰的建议报告，要包含食谱信息、得分、推荐理由、食谱的参考图片，帮助用户快速做出决策。

请严格按照流程，优先使用知识库结果，知识库不满足时再调用 web_search 工具搜索。
"""


def _build_system_prompt(sources: Optional[List[RecipeSearchResult]] = None) -> str:
    """Build system prompt with optional RAG sources injected."""
    if not sources:
        return BASE_SYSTEM_PROMPT

    sources_text = "\n\n## 知识库检索结果\n\n"
    for idx, source in enumerate(sources, 1):
        ingredients_text = "\n".join(f"- {ingredient}" for ingredient in source.ingredients)
        sources_text += (
            f"### [{idx}] {source.title}\n"
            f"- 相关度得分：{source.score:.3f}\n"
            f"- 热量：{source.calories} kcal\n"
            f"- 难度：{source.difficulty}\n"
            f"- 标签：{', '.join(source.tags)}\n"
            f"- 食材：\n{ingredients_text}\n"
            f"- 做法：\n{source.steps}\n\n"
        )

    return BASE_SYSTEM_PROMPT + sources_text


@tool
def web_search(query: str) -> str:
    """Search the web for recipes or cooking information when the knowledge base is insufficient."""
    logger.info(f"[Web Search]: {query}")
    try:
        results = tavily.invoke(query)
        return str(results) if results else "未找到相关结果"
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"搜索失败：{e}"


def _create_agent(system_prompt: str):
    """Create a fresh agent instance with the given system prompt."""
    return create_agent(
        model=model,
        tools=[web_search],
        checkpointer=checkpointer,
        system_prompt=system_prompt,
    )


def retrieve_recipes_for_query(query: str, image_url: Optional[str] = None, top_k: int = 5) -> List[RecipeSearchResult]:
    """Retrieve recipes from the knowledge base for a given query."""
    return retrieve_recipes(query=query, image_url=image_url, top_k=top_k)


async def search_recipes(
    prompt: str,
    image: Optional[str],
    thread_id: str,
    sources: Optional[List[RecipeSearchResult]] = None,
):
    """调用agent搜索食谱，可传入已检索好的RAG sources。"""
    logger.info(f"[用户]: {prompt}, image: {image}, thread_id: {thread_id}, sources: {len(sources) if sources else 0}")

    try:
        # 如果没有传入sources，则内部做一次检索
        if sources is None:
            sources = retrieve_recipes_for_query(prompt, image)

        system_prompt = _build_system_prompt(sources)
        agent = _create_agent(system_prompt)

        # 判断是否有图片，封装不同格式的消息
        if not image or image.strip() == "":
            message = HumanMessage(content=prompt)
        else:
            message = HumanMessage(content=[
                {"type": "image", "url": image},
                {"type": "text", "text": prompt},
            ])

        # 流式调用Agent
        for chunk, metadata in agent.stream(
            {"messages": [message]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content

    except Exception as e:
        logger.error(f"\n[错误]: {str(e)}")
        yield "信息检索失败，试试看手动输入食物列表？"


# 清空会话
def clear_messages(thread_id: str):
    """清空会话"""
    logger.info(f"清空历史消息，thread_id: {thread_id}")
    checkpointer.delete_thread(thread_id)


# 查询会话历史
def get_messages(thread_id: str) -> list[dict[str, str]]:
    """获取会话历史"""
    logger.info(f"获取历史消息，thread_id: {thread_id}")

    checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
    if not checkpoint:
        return []

    channel_values = checkpoint.get("channel_values")
    if not channel_values:
        return []

    messages = channel_values.get("messages", [])
    if not messages:
        return []

    result = []
    for msg in messages:
        if not msg.content:
            continue

        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})

    return result
