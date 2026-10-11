<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{ content: string }>()
const html = computed(() => renderMarkdown(props.content))
</script>

<template>
  <!-- Raw HTML is escaped by the shared renderer before reaching v-html. -->
  <div class="markdown-content" v-html="html" />
</template>

<style scoped>
.markdown-content { min-width: 0; line-height: 1.75; white-space: normal; overflow-wrap: anywhere; }
.markdown-content :deep(p) { margin: 0 0 12px; }
.markdown-content :deep(ul), .markdown-content :deep(ol) { margin: 10px 0 14px; padding-left: 22px; }
.markdown-content :deep(li + li) { margin-top: 6px; }
.markdown-content :deep(li > p) { margin-bottom: 6px; }
.markdown-content :deep(strong) { color: var(--qh-berry); font-weight: 700; }
.markdown-content :deep(h1), .markdown-content :deep(h2), .markdown-content :deep(h3),
.markdown-content :deep(h4), .markdown-content :deep(h5), .markdown-content :deep(h6) { margin: 16px 0 8px; font-size: 1.05em; line-height: 1.5; color: var(--qh-berry); }
.markdown-content :deep(blockquote) { margin: 12px 0; padding-left: 12px; border-left: 2px solid var(--qh-border); }
.markdown-content :deep(a) { color: var(--qh-berry); text-decoration: underline; text-underline-offset: 3px; }
.markdown-content :deep(code) { padding: 2px 4px; border-radius: 4px; background: var(--qh-cream); font-size: .9em; }
.markdown-content :deep(pre) { max-width: 100%; overflow-x: auto; padding: 10px; border-radius: 8px; background: var(--qh-cream); }
.markdown-content :deep(pre code) { padding: 0; }
.markdown-content :deep(table) { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; margin: 12px 0; }
.markdown-content :deep(th), .markdown-content :deep(td) { padding: 6px 10px; border: 1px solid var(--qh-border); text-align: left; }
.markdown-content :deep(hr) { border: 0; border-top: 1px solid var(--qh-border); margin: 14px 0; }
.markdown-content > :deep(:first-child) { margin-top: 0; }
.markdown-content > :deep(:last-child) { margin-bottom: 0; }
</style>
