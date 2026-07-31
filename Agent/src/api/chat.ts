import { client } from './client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface RecipeSource {
  id: string
  title: string
  ingredients: string[]
  steps: string
  calories: number
  difficulty: string
  tags: string[]
  image_url: string
  score: number
}

export interface RetrieveResponse {
  sources: RecipeSource[]
  query_time_ms: number
}

export async function retrieveRecipes(
  query: string,
  imageUrl: string | null,
  topK: number = 5
): Promise<RetrieveResponse> {
  const { data } = await client.post<RetrieveResponse>('/retrieve', {
    query,
    image_url: imageUrl,
    top_k: topK,
  })
  return data
}

export async function streamChat(
  message: string,
  imageUrl: string | null,
  threadId: string,
  sources: RecipeSource[] | null,
  onChunk: (chunk: string) => void
): Promise<void> {
  const body: Record<string, unknown> = {
    message,
    image_url: imageUrl,
    thread_id: threadId,
  }
  if (sources && sources.length > 0) {
    body.sources = sources
  }

  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    onChunk(chunk)
  }
}

export async function getMessages(threadId: string): Promise<ChatMessage[]> {
  const { data } = await client.get('/chat/messages', {
    params: { thread_id: threadId },
  })
  return data.messages || []
}

export async function clearMessages(threadId: string): Promise<void> {
  await client.delete('/chat/messages', {
    params: { thread_id: threadId },
  })
}
