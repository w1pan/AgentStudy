<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import SourcesPanel from './SourcesPanel.vue'

const chatStore = useChatStore()
const inputText = ref('')
const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const messagesContainer = ref<HTMLDivElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const queryTimeMs = ref(0)

watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }
)

function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file)
  }
}

function removeFile() {
  selectedFile.value = null
  previewUrl.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text && !selectedFile.value) return
  if (chatStore.isLoading || chatStore.isRetrieving) return

  const file = selectedFile.value
  inputText.value = ''
  removeFile()
  queryTimeMs.value = 0

  const startTime = performance.now()
  await chatStore.sendMessage(text || '这是什么食材？', file)
  queryTimeMs.value = Math.round(performance.now() - startTime)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function getStatusText() {
  if (chatStore.isRetrieving) return '🔍 正在检索知识库...'
  if (chatStore.isLoading) return '✨ AI 正在生成回复...'
  return ''
}
</script>

<template>
  <div class="chat-page">
    <div class="chat-wrapper">
      <header class="chat-header">
        <h1>私厨助手</h1>
        <button
          class="btn-clear"
          :disabled="chatStore.isLoading || !chatStore.hasMessages"
          @click="chatStore.resetChat"
        >
          清空会话
        </button>
      </header>

      <div v-if="getStatusText()" class="status-bar">
        <span class="status-text">{{ getStatusText() }}</span>
        <span v-if="chatStore.isRetrieving" class="status-dots">
          <span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
        </span>
      </div>

      <div ref="messagesContainer" class="messages-container">
        <div v-if="!chatStore.hasMessages" class="empty-state">
          <p>上传食材照片或描述食材，我来为你推荐食谱</p>
        </div>

        <div
          v-for="(msg, index) in chatStore.messages"
          :key="index"
          class="message-row"
          :class="msg.role"
        >
          <div class="bubble">
            <pre v-if="msg.content">{{ msg.content }}</pre>
            <div v-else class="typing">思考中<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></div>
          </div>
        </div>

        <div v-if="chatStore.error" class="error-toast">
          {{ chatStore.error }}
          <button @click="chatStore.error = null">✕</button>
        </div>
      </div>

      <div class="input-area">
        <div v-if="previewUrl" class="file-preview">
          <img :src="previewUrl" alt="preview" />
          <button class="remove-file" @click="removeFile">✕</button>
        </div>

        <div class="input-row">
          <button class="btn-attach" @click="fileInput?.click()">📎</button>
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            style="display: none"
            @change="handleFileChange"
          />
          <textarea
            v-model="inputText"
            rows="1"
            placeholder="描述你的食材或上传照片..."
            @keydown="handleKeydown"
          />
          <button
            class="btn-send"
            :disabled="chatStore.isLoading || (!inputText.trim() && !selectedFile)"
            @click="handleSend"
          >
            {{ chatStore.isLoading ? '发送中' : '发送' }}
          </button>
        </div>
      </div>
    </div>

    <SourcesPanel :sources="chatStore.sources" :query-time-ms="queryTimeMs" />
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.chat-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
  background: var(--color-background-soft);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: var(--color-background);
  border-bottom: 1px solid var(--color-border);
}

.chat-header h1 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  background: hsla(160, 100%, 37%, 0.08);
  border-bottom: 1px solid hsla(160, 100%, 37%, 0.15);
  font-size: 0.85rem;
  color: hsla(160, 100%, 30%, 1);
}

.status-text {
  font-weight: 500;
}

.status-dots .dot {
  animation: blink 1.4s infinite both;
}

.status-dots .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.status-dots .dot:nth-child(3) {
  animation-delay: 0.4s;
}

.btn-clear {
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover:not(:disabled) {
  border-color: var(--color-border-hover);
  background: var(--color-background-mute);
}

.btn-clear:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state {
  margin: auto;
  color: var(--color-text-2, #888);
  text-align: center;
  font-size: 0.95rem;
}

.message-row {
  display: flex;
  width: 100%;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.message-row.user .bubble {
  background: hsla(160, 100%, 37%, 1);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-row.assistant .bubble {
  background: var(--color-background);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: 4px;
}

.bubble pre {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
}

.typing {
  color: #888;
  font-size: 0.9rem;
}

.dot {
  animation: blink 1.4s infinite both;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%, 80%, 100% {
    opacity: 0;
  }
  40% {
    opacity: 1;
  }
}

.error-toast {
  align-self: center;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
  border-radius: 8px;
  font-size: 0.85rem;
}

.error-toast button {
  background: none;
  border: none;
  color: #c33;
  cursor: pointer;
  font-size: 0.9rem;
}

.input-area {
  padding: 1rem 1.5rem;
  background: var(--color-background);
  border-top: 1px solid var(--color-border);
}

.file-preview {
  position: relative;
  display: inline-block;
  margin-bottom: 0.5rem;
}

.file-preview img {
  height: 60px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  object-fit: cover;
}

.remove-file {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: #333;
  color: #fff;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.btn-attach {
  padding: 0.6rem;
  font-size: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background-soft);
  cursor: pointer;
  transition: background 0.2s;
}

.btn-attach:hover {
  background: var(--color-background-mute);
}

.input-row textarea {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-background-soft);
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.95rem;
  resize: none;
  max-height: 120px;
  outline: none;
}

.input-row textarea:focus {
  border-color: hsla(160, 100%, 37%, 1);
}

.btn-send {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 8px;
  background: hsla(160, 100%, 37%, 1);
  color: #fff;
  font-size: 0.95rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-send:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .chat-page {
    flex-direction: column;
  }

  .chat-wrapper {
    height: 60vh;
  }
}
</style>
