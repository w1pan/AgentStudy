<script setup lang="ts">
import { nextTick, ref } from 'vue'

import { streamAdviceFollowUp, type AdviceCard, type FollowUpMessage } from '@/api/qingheng'

const props = defineProps<{ card: AdviceCard; messages: FollowUpMessage[] }>()
const emit = defineEmits<{ close: []; 'update:messages': [messages: FollowUpMessage[]] }>()
const input = ref('')
const streaming = ref(false)
const localError = ref('')
const scrollArea = ref<HTMLElement | null>(null)

async function scrollBottom() {
  await nextTick()
  if (scrollArea.value) scrollArea.value.scrollTop = scrollArea.value.scrollHeight
}

async function send() {
  const message = input.value.trim()
  if (!message || streaming.value) return
  localError.value = ''
  const history = props.messages.map((item) => ({ ...item }))
  const nextMessages: FollowUpMessage[] = [...history, { role: 'user', content: message }, { role: 'assistant', content: '' }]
  emit('update:messages', nextMessages)
  input.value = ''
  streaming.value = true
  await scrollBottom()
  try {
    await streamAdviceFollowUp(props.card.type, message, history, (text) => {
      nextMessages[nextMessages.length - 1]!.content += text
      emit('update:messages', [...nextMessages])
      void scrollBottom()
    })
  } catch (error) {
    localError.value = error instanceof Error ? error.message : '追问失败'
    if (!nextMessages[nextMessages.length - 1]!.content) nextMessages.pop()
    emit('update:messages', [...nextMessages])
  } finally {
    streaming.value = false
  }
}
</script>

<template>
  <div class="drawer-backdrop" @mousedown.self="emit('close')">
    <aside class="drawer" role="dialog" aria-modal="true">
      <header><div><p>围绕这张卡追问</p><h2>{{ card.title }}</h2></div><button @click="emit('close')">×</button></header>
      <div ref="scrollArea" class="conversation">
        <section class="card-context"><p>{{ card.body }}</p><ul v-if="card.bullets.length"><li v-for="item in card.bullets" :key="item">{{ item }}</li></ul></section>
        <template v-for="(message, index) in messages" :key="index">
          <div class="message" :class="`message--${message.role}`">{{ message.content || '…' }}</div>
        </template>
        <p v-if="localError" class="form-error">{{ localError }}</p>
      </div>
      <form @submit.prevent="send"><textarea v-model="input" rows="2" maxlength="1200" placeholder="例如：下一餐最应该注意什么？" @keydown.enter.exact.prevent="send" /><button :disabled="!input.trim() || streaming">{{ streaming ? '回答中' : '发送' }}</button></form>
    </aside>
  </div>
</template>

<style scoped>
.drawer-backdrop { position: fixed; z-index: 50; inset: 0; background: rgb(33 38 30 / 25%); }
.drawer { position: absolute; top: 0; right: 0; display: grid; grid-template-rows: auto 1fr auto; width: min(480px, 100%); height: 100%; border-left: 1px solid var(--qh-border); background: var(--qh-card); box-shadow: -20px 0 60px rgb(30 45 26 / 17%); }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 24px; border-bottom: 1px solid var(--qh-border); } header p, h2 { margin: 0; } header p { color: var(--qh-green-dark); font-size: 12px; font-weight: 800; } h2 { margin-top: 4px; font-size: 22px; } header button { width: 38px; height: 38px; border: 0; border-radius: 12px; color: var(--qh-muted); background: var(--qh-sage-soft); font-size: 25px; cursor: pointer; }
.conversation { overflow: auto; padding: 22px; }.card-context { padding: 17px; border-radius: 16px; background: var(--qh-sage-soft); }.card-context p { margin: 0; line-height: 1.65; }.card-context ul { margin: 11px 0 0; padding-left: 20px; color: var(--qh-muted); line-height: 1.6; }
.message { width: fit-content; max-width: 86%; margin-top: 14px; padding: 11px 14px; border-radius: 15px; line-height: 1.6; white-space: pre-wrap; }.message--user { margin-left: auto; color: white; background: var(--qh-green); border-bottom-right-radius: 5px; }.message--assistant { background: var(--qh-ivory-strong); border-bottom-left-radius: 5px; }
.form-error { color: #8f3f35; font-size: 13px; }
form { display: grid; grid-template-columns: 1fr auto; gap: 10px; padding: 18px; border-top: 1px solid var(--qh-border); } textarea { resize: none; padding: 11px 12px; border: 1px solid var(--qh-border-strong); border-radius: 13px; color: var(--qh-text); background: white; } form button { align-self: stretch; padding: 0 18px; border: 0; border-radius: 12px; color: white; background: var(--qh-green); font-weight: 800; cursor: pointer; } form button:disabled { opacity: .5; }
@media (max-width: 600px) { .drawer-backdrop { display: flex; align-items: flex-end; }.drawer { position: static; width: 100%; height: min(86vh, 720px); border-top: 1px solid var(--qh-border); border-left: 0; border-radius: 22px 22px 0 0; } }
</style>
