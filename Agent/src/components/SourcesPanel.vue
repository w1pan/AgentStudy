<script setup lang="ts">
import { computed } from 'vue'
import type { RecipeSource } from '@/api/chat'

const props = defineProps<{
  sources: RecipeSource[]
  queryTimeMs: number
}>()

const hasSources = computed(() => props.sources.length > 0)

function formatScore(score: number): string {
  return (score * 100).toFixed(1)
}

function toggleExpanded(event: Event) {
  const target = event.currentTarget as HTMLElement
  const card = target.closest('.source-card')
  card?.classList.toggle('expanded')
}
</script>

<template>
  <aside class="sources-panel">
    <header class="panel-header">
      <h2>📚 知识库来源</h2>
      <span v-if="hasSources" class="query-time">{{ queryTimeMs }}ms</span>
    </header>

    <div v-if="!hasSources" class="empty-state">
      <p>发送消息后，这里会显示 RAG 检索到的相关菜谱</p>
    </div>

    <div v-else class="sources-list">
      <div
        v-for="source in sources"
        :key="source.id"
        class="source-card"
      >
        <div class="source-header" @click="toggleExpanded">
          <div class="source-main">
            <h3 class="source-title">{{ source.title }}</h3>
            <div class="source-meta">
              <span class="score-badge">相关度 {{ formatScore(source.score) }}%</span>
              <span class="calorie-badge">{{ source.calories }} kcal</span>
              <span class="difficulty-badge">{{ source.difficulty }}</span>
            </div>
          </div>
          <span class="expand-icon">▼</span>
        </div>

        <div class="source-body">
          <div class="source-section">
            <h4>食材</h4>
            <ul class="ingredients-list">
              <li v-for="(ingredient, index) in source.ingredients" :key="index">
                {{ ingredient }}
              </li>
            </ul>
          </div>

          <div class="source-section">
            <h4>做法</h4>
            <p class="steps-text">{{ source.steps }}</p>
          </div>

          <div v-if="source.tags.length > 0" class="source-section">
            <h4>标签</h4>
            <div class="tags-list">
              <span v-for="tag in source.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sources-panel {
  width: 380px;
  min-width: 320px;
  max-width: 420px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-background);
  border-left: 1px solid var(--color-border);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-background-soft);
}

.panel-header h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.query-time {
  font-size: 0.75rem;
  color: var(--color-text-2, #888);
  background: var(--color-background-mute);
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: var(--color-text-2, #888);
  text-align: center;
  font-size: 0.9rem;
}

.sources-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;
}

.source-card:hover {
  border-color: var(--color-border-hover);
}

.source-header {
  padding: 0.875rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.source-main {
  flex: 1;
  min-width: 0;
}

.source-title {
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-heading);
}

.source-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.score-badge,
.calorie-badge,
.difficulty-badge {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
  font-weight: 500;
}

.score-badge {
  background: hsla(160, 100%, 37%, 0.15);
  color: hsla(160, 100%, 30%, 1);
}

.calorie-badge {
  background: hsla(30, 100%, 50%, 0.12);
  color: hsla(30, 100%, 40%, 1);
}

.difficulty-badge {
  background: var(--color-background-mute);
  color: var(--color-text-2, #888);
}

.expand-icon {
  font-size: 0.75rem;
  color: var(--color-text-2, #888);
  transition: transform 0.2s;
  margin-top: 0.25rem;
}

.source-card.expanded .expand-icon {
  transform: rotate(180deg);
}

.source-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s ease-out;
}

.source-card.expanded .source-body {
  max-height: 600px;
}

.source-section {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-border);
}

.source-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-2, #888);
}

.ingredients-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.85rem;
  color: var(--color-text);
}

.ingredients-list li {
  margin-bottom: 0.2rem;
}

.steps-text {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: var(--color-text);
  white-space: pre-wrap;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.tag {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  background: var(--color-background-mute);
  color: var(--color-text-2, #888);
  border-radius: 8px;
}

@media (max-width: 900px) {
  .sources-panel {
    width: 100%;
    max-width: none;
    height: auto;
    max-height: 40vh;
    border-left: none;
    border-top: 1px solid var(--color-border);
  }
}
</style>
