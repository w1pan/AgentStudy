<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { vDialog } from '@/utils/dialog'

const props = defineProps<{
  title: string
  description: string
  confirmLabel: string
  confirmationText?: string
  action: () => Promise<void>
}>()
const emit = defineEmits<{ close: []; done: [] }>()
const id = useId()
const input = ref('')
const busy = ref(false)
const error = ref('')
const valid = computed(() => !props.confirmationText || input.value === props.confirmationText)
function close() { if (!busy.value) emit('close') }
async function confirm() {
  if (busy.value || !valid.value) return
  busy.value = true
  error.value = ''
  try {
    await props.action()
    emit('done')
  } catch (value) {
    error.value = value instanceof Error ? value.message : '操作未完成，请重试。'
  } finally { busy.value = false }
}
</script>

<template>
  <div v-dialog="close" class="confirm-backdrop" @mousedown.self="close">
    <section class="confirm-dialog" role="alertdialog" aria-modal="true" :aria-labelledby="`${id}-title`" :aria-describedby="`${id}-description`">
      <header><h2 :id="`${id}-title`">{{ title }}</h2><button class="confirm-close" type="button" aria-label="关闭确认窗口" :disabled="busy" @click="close">×</button></header>
      <form @submit.prevent="confirm">
        <div class="confirm-body"><p :id="`${id}-description`">{{ description }}</p><label v-if="confirmationText" :for="`${id}-input`">请输入「{{ confirmationText }}」以确认<input :id="`${id}-input`" v-model="input" :disabled="busy" autocomplete="off" :placeholder="confirmationText" /></label><p v-if="error" class="confirm-error" role="alert">{{ error }}</p></div>
        <footer><button class="confirm-cancel" type="button" :disabled="busy" @click="close">取消</button><button class="confirm-submit" type="submit" :disabled="busy || !valid">{{ busy ? '处理中…' : confirmLabel }}</button></footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
.confirm-backdrop { position: fixed; inset: 0; z-index: 60; display: grid; place-items: center; padding: 20px; background: var(--qh-overlay); backdrop-filter: blur(4px); }
.confirm-dialog { width: min(440px, 100%); max-height: calc(100dvh - 40px); overflow: auto; border: var(--qh-stroke) solid var(--qh-berry); border-radius: 22px; background: var(--qh-cream); box-shadow: var(--qh-shadow); }
header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 20px; background: var(--qh-oat); border-bottom: 1px solid var(--qh-border); }
h2 { margin: 0; font-size: 21px; overflow-wrap: anywhere; }
.confirm-close { flex: 0 0 40px; width: 40px; height: 40px; border: 0; border-radius: 50%; background: var(--qh-cream); color: var(--qh-muted); font-size: 25px; cursor: pointer; }
.confirm-body { padding: 20px; }
p { margin: 0; color: var(--qh-muted); font-size: 14px; line-height: 1.8; overflow-wrap: anywhere; }
label { display: grid; gap: 10px; margin-top: 18px; font-size: 12px; line-height: 1.7; }
input { width: 100%; min-width: 0; min-height: 46px; padding: 10px 12px; border: 1px solid var(--qh-border); border-radius: 12px; background: var(--qh-cream); color: var(--qh-berry); font-size: 16px; }
.confirm-error { margin-top: 14px; padding: 10px; background: var(--qh-oat); border-radius: 10px; color: var(--qh-berry); }
footer { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--qh-border); background: var(--qh-oat); }
footer button { min-height: 44px; padding: 10px 18px; border-radius: var(--qh-radius-pill); font-size: 14px; cursor: pointer; }
.confirm-cancel { border: 1px solid var(--qh-border); background: var(--qh-cream); }
.confirm-submit { border: 1px solid var(--qh-berry); background: var(--qh-berry); color: var(--qh-cream); font-weight: 600; }
button:disabled { opacity: .5; cursor: default; }
@media (max-width: 760px) { .confirm-backdrop { padding: 16px; } .confirm-close { width: 44px; height: 44px; flex-basis: 44px; } }
</style>
