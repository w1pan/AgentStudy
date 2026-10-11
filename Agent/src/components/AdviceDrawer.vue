<script setup lang="ts">
import { vDialog } from '@/utils/dialog'
import { nextTick, onBeforeUnmount, ref } from 'vue'
import MarkdownContent from './MarkdownContent.vue'

import { streamAdviceFollowUp, type AdviceCard, type FollowUpMessage } from '@/api/qingheng'

const props = defineProps<{ card: AdviceCard; messages: FollowUpMessage[] }>()
const emit = defineEmits<{ close: []; 'update:messages': [messages: FollowUpMessage[]] }>()
const input = ref('')
const streaming = ref(false)
const localError = ref('')
const scrollArea = ref<HTMLElement | null>(null)
const followLatest = ref(true)
const retryRequest = ref<{ message: string; history: FollowUpMessage[] } | null>(null)
let controller: AbortController | undefined
let disposed = false
let stopped = false
onBeforeUnmount(() => { disposed = true; controller?.abort() })

function trackScroll() {
  const area = scrollArea.value
  if (area) followLatest.value = area.scrollHeight - area.scrollTop - area.clientHeight < 64
}
async function jumpToLatest() {
  followLatest.value = true
  await scrollBottom()
}

async function scrollBottom() {
  await nextTick()
  if (!disposed && followLatest.value && scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
}

function sendOnEnter(event: KeyboardEvent) {
  if (event.isComposing) return
  event.preventDefault()
  void send()
}

async function send() {
  const message = input.value.trim()
  if (!message || streaming.value) return
  input.value = ''
  await respond(message, props.messages.map(item => ({ ...item })))
}

async function retry() {
  if (!retryRequest.value || streaming.value) return
  await respond(retryRequest.value.message, retryRequest.value.history)
}

async function respond(message: string, history: FollowUpMessage[]) {
  localError.value = ''
  retryRequest.value = null
  const nextMessages: FollowUpMessage[] = [...history, { role: 'user', content: message }, { role: 'assistant', content: '' }]
  emit('update:messages', nextMessages)
  streaming.value = true
  stopped = false
  controller = new AbortController()
  followLatest.value = true
  await scrollBottom()
  try {
    await streamAdviceFollowUp(props.card.type, message, history, (text) => {
      if (disposed) return
      nextMessages[nextMessages.length - 1]!.content += text
      emit('update:messages', [...nextMessages])
      void scrollBottom()
    }, controller.signal)
    if (!nextMessages[nextMessages.length - 1]!.content) throw new Error('没有收到回答，请重试。')
  } catch (error) {
    if (disposed) return
    localError.value = stopped ? '回答已停止，可以重新生成。' : error instanceof Error ? error.message : '回答未完成，请重试。'
    retryRequest.value = { message, history }
    if (!nextMessages[nextMessages.length - 1]!.content) nextMessages.pop()
    emit('update:messages', [...nextMessages])
    void scrollBottom()
  } finally {
    streaming.value = false
  }
}

function stop() { stopped = true; controller?.abort() }
</script>

<template>
  <div v-dialog="() => emit('close')" class="drawer-backdrop" @mousedown.self="emit('close')">
    <aside class="drawer" role="dialog" aria-modal="true" :aria-label="card.title">
      <header><div><p>继续聊聊这条建议</p><h2>{{ card.title }}</h2></div><button aria-label="关闭建议追问" @click="emit('close')">×</button></header>
      <div ref="scrollArea" class="conversation" @scroll="trackScroll">
        <section class="card-context"><MarkdownContent :content="card.body" /><ul v-if="card.bullets.length"><li v-for="(item, index) in card.bullets" :key="index"><MarkdownContent :content="item" /></li></ul></section>
        <template v-for="(message, index) in messages" :key="index">
          <div class="message" :class="`message--${message.role}`">
            <MarkdownContent v-if="message.role === 'assistant'" :content="message.content || '正在整理回答…'" />
            <template v-else>{{ message.content }}</template>
          </div>
        </template>
        <div v-if="localError" class="form-error" role="alert"><p>{{ localError }}</p><button v-if="retryRequest" type="button" class="retry-answer" :disabled="streaming" @click="retry">重新生成回答</button></div>
      </div>
      <div class="composer">
        <div v-if="!followLatest || streaming" class="conversation-tools"><span v-if="streaming" role="status">正在生成回答…</span><button v-if="!followLatest" type="button" class="jump-latest" @click="jumpToLatest">查看最新回答 ↓</button><button v-if="streaming" type="button" class="stop-answer" @click="stop">停止回答</button></div>
        <form @submit.prevent="send"><textarea aria-label="追问内容" v-model="input" rows="2" maxlength="1200" placeholder="例如：下一餐最应该注意什么？" @keydown.enter.exact="sendOnEnter" /><button :disabled="!input.trim() || streaming">{{ streaming ? '回答中' : '发送' }}</button></form>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.drawer-backdrop { position: fixed; z-index: 50; inset: 0; background: var(--qh-overlay); }
.drawer { position: absolute; top: 0; right: 0; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; width: min(480px, 100%); height: 100%; border-left: 1px solid var(--qh-border); background: var(--qh-card); box-shadow: var(--qh-shadow); }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 24px; border-bottom: 1px solid var(--qh-border); background: var(--qh-oat); } header p, h2 { margin: 0; } header p { color: var(--qh-brand); font-size: 12px; font-weight: 800; } h2 { margin-top: 4px; font-size: 22px; } header button { width: 38px; height: 38px; border: 0; border-radius: var(--qh-radius-control); color: var(--qh-muted); background: var(--qh-card); font-size: 25px; flex-shrink: 0; cursor: pointer; }
.conversation { overflow: auto; padding: 22px; }.card-context { padding: 17px; border: 1px solid var(--qh-border); border-radius: var(--qh-radius-control); background: var(--qh-oat); overflow-wrap: anywhere; }.card-context p { margin: 0; line-height: 1.65; }.card-context ul { margin: 11px 0 0; padding-left: 20px; color: var(--qh-muted); line-height: 1.6; }
.message { width: fit-content; max-width: 86%; margin-top: 14px; padding: 11px 14px; border-radius: var(--qh-radius-control); line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }.message--user { margin-left: auto; color: var(--qh-on-brand); background: var(--qh-brand); border-bottom-right-radius: 5px; }.message--assistant { background: var(--qh-ivory-strong); border-bottom-left-radius: 5px; }
.form-error { margin-top: 16px; padding: 12px; border: 1px solid var(--qh-border); border-radius: 14px; background: var(--qh-oat); color: var(--qh-muted); font-size: 13px; line-height: 1.7; }
.form-error p { margin: 0; }
.retry-answer, .conversation-tools button { min-height: 44px; padding: 8px 12px; border: 1px solid var(--qh-border); border-radius: var(--qh-radius-pill); color: var(--qh-berry); background: var(--qh-cream); font-size: 12px; cursor: pointer; }
.retry-answer { margin-top: 8px; }
.conversation-tools { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; padding: 8px 18px; background: var(--qh-oat); border-top: 1px solid var(--qh-border); }
.conversation-tools > span { margin-right: auto; font-size: 12px; color: var(--qh-muted); }
.composer { min-width: 0; }
form { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; padding: 18px; border-top: 1px solid var(--qh-border); } textarea { min-width: 0; resize: none; padding: 11px 12px; border: 1px solid var(--qh-border); border-radius: var(--qh-radius-control); color: var(--qh-prose); background: var(--qh-card); } form button { align-self: stretch; padding: 0 18px; border: 0; border-radius: var(--qh-radius-control); color: var(--qh-on-brand); background: var(--qh-brand); font-weight: 800; cursor: pointer; } form button:disabled { opacity: .5; }
textarea:focus-visible { border-color: var(--qh-brand); outline: 1px solid var(--qh-focus); outline-offset: 2px; }
.drawer { --qh-prose: #49453f; }
.card-context, .message--assistant { color: var(--qh-prose); font-size: 14px; line-height: 1.75; }
.card-context ul { color: inherit; }
.card-context li + li { margin-top: 8px; }
.conversation { overscroll-behavior: contain; }
@media (max-width: 760px) {
  .drawer-backdrop { display: flex; align-items: flex-end; }
  .drawer { position: static; width: 100%; height: min(94vh, 720px); height: min(94dvh, 720px); overflow: hidden; border-top: 1px solid var(--qh-border); border-left: 0; border-radius: var(--qh-radius-card) var(--qh-radius-card) 0 0; }
  header { padding: 16px; }
  h2 { font-size: 20px; overflow-wrap: anywhere; }
  header button { width: 44px; height: 44px; }
  .conversation { padding: 16px; }
  .card-context { padding: 14px; }
  .message { max-width: 94%; }
  form { gap: 8px; padding: 12px 12px calc(12px + env(safe-area-inset-bottom)); }
  textarea { min-height: 80px; font-size: 16px; }
  form button { padding-inline: 14px; }
}
</style>
