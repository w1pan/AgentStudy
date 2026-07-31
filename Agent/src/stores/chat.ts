import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  streamChat,
  getMessages,
  clearMessages,
  retrieveRecipes,
  type ChatMessage,
  type RecipeSource,
} from '@/api/chat'
import { getPresignUrl, uploadToOss } from '@/api/oss'

function generateThreadId(): string {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export const useChatStore = defineStore('chat', () => {
  const threadId = ref<string>(generateThreadId())
  const messages = ref<ChatMessage[]>([])
  const sources = ref<RecipeSource[]>([])
  const isLoading = ref(false)
  const isRetrieving = ref(false)
  const error = ref<string | null>(null)

  const hasMessages = computed(() => messages.value.length > 0)

  function addUserMessage(content: string) {
    messages.value.push({ role: 'user', content })
  }

  function addAssistantMessage(content: string) {
    messages.value.push({ role: 'assistant', content })
  }

  function appendToLastMessage(chunk: string) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += chunk
    }
  }

  async function sendMessage(text: string, imageFile: File | null) {
    if (isLoading.value || isRetrieving.value) return

    isRetrieving.value = true
    isLoading.value = true
    error.value = null
    sources.value = []

    let imageUrl: string | null = null

    try {
      // 1. 上传图片到 OSS
      if (imageFile) {
        const presign = await getPresignUrl(imageFile.name)
        await uploadToOss(imageFile, presign)
        imageUrl = presign.accessUrl
      }

      // 2. 先检索知识库
      const retrieveResponse = await retrieveRecipes(text || '这是什么食材？', imageUrl, 5)
      sources.value = retrieveResponse.sources
      isRetrieving.value = false

      // 3. 添加用户消息和空的助手消息
      addUserMessage(text || '这是什么食材？')
      addAssistantMessage('')

      // 4. 流式请求 Agent 生成回复
      await streamChat(text || '这是什么食材？', imageUrl, threadId.value, sources.value, (chunk) => {
        appendToLastMessage(chunk)
      })
    } catch (e) {
      error.value = e instanceof Error ? e.message : '发送失败'
      // 如果助手消息为空，则移除
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant' && last.content === '') {
        messages.value.pop()
      }
    } finally {
      isLoading.value = false
      isRetrieving.value = false
    }
  }

  async function loadHistory() {
    try {
      const history = await getMessages(threadId.value)
      messages.value = history
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载历史失败'
    }
  }

  async function resetChat() {
    try {
      await clearMessages(threadId.value)
      messages.value = []
      sources.value = []
      threadId.value = generateThreadId()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '重置失败'
    }
  }

  return {
    threadId,
    messages,
    sources,
    isLoading,
    isRetrieving,
    error,
    hasMessages,
    sendMessage,
    loadHistory,
    resetChat,
  }
})
