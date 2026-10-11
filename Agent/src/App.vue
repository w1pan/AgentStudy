<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import UiIcon from '@/components/UiIcon.vue'
import LeafMark from '@/components/LeafMark.vue'
import FeedbackToast from '@/components/FeedbackToast.vue'
import ProfileView from '@/views/ProfileView.vue'
import RecordsView from '@/views/RecordsView.vue'
import TodayView from '@/views/TodayView.vue'
import { useQinghengStore } from '@/stores/qingheng'
import { currentRecordDate } from '@/utils/energy'

type RouteName = 'today' | 'records' | 'profile'

const store = useQinghengStore()
const route = ref<RouteName>('today')
let dayTimer: ReturnType<typeof setTimeout> | undefined
let lastRefreshAt = Date.now()
let lastDayRefresh = currentRecordDate()
let pendingDayRefresh = false
const focusRefreshInterval = 60_000

function reloadToday() {
  if (!store.initialized || store.busy) return
  lastRefreshAt = Date.now()
  lastDayRefresh = currentRecordDate()
  pendingDayRefresh = false
  void store.reloadToday()
}

function readHash() {
  const previous = route.value
  const value = window.location.hash.replace('#/', '')
  route.value = value === 'records' || value === 'profile' ? value : 'today'
  if (previous !== 'today' && route.value === 'today') reloadToday()
}

function refreshVisibleToday() {
  if (document.visibilityState === 'visible') {
    reloadToday()
    armMidnightTimer()
  }
}

function checkDay() {
  const date = currentRecordDate()
  if (lastDayRefresh === date || store.today?.summary.record_date === date) {
    pendingDayRefresh = false
    return
  }
  if (!store.initialized || store.busy) {
    pendingDayRefresh = true
    return
  }
  reloadToday()
}

function refreshOnFocus() {
  if (document.visibilityState !== 'visible') return
  if (Date.now() - lastRefreshAt >= focusRefreshInterval) reloadToday()
  else checkDay()
}

function armMidnightTimer() {
  if (dayTimer) clearTimeout(dayTimer)
  const nextMidnight = Date.parse(`${currentRecordDate()}T00:00:00+08:00`) + 86_400_000
  dayTimer = setTimeout(() => {
    checkDay()
    armMidnightTimer()
  }, Math.max(1, nextMidnight - Date.now()))
}

// Consume only a queued midnight refresh; ordinary request completion never retries.
watch(() => store.busy, (busy) => { if (!busy && pendingDayRefresh) checkDay() })

function navigate(value: RouteName) {
  window.location.hash = `/${value}`
}

function onboardingSaved() {
  navigate('today')
}

onMounted(async () => {
  readHash()
  window.addEventListener('hashchange', readHash)
  document.addEventListener('visibilitychange', refreshVisibleToday)
  window.addEventListener('focus', refreshOnFocus)
  armMidnightTimer()
  await store.initialize()
})
onBeforeUnmount(() => {
  window.removeEventListener('hashchange', readHash)
  document.removeEventListener('visibilitychange', refreshVisibleToday)
  window.removeEventListener('focus', refreshOnFocus)
  if (dayTimer) clearTimeout(dayTimer)
})
</script>

<template>
  <div v-if="!store.initialized" class="boot-screen" role="status">
    <div class="brand-mark"><LeafMark /></div>
    <strong>轻衡</strong><span>正在整理今天的能量账本…</span>
  </div>

  <div v-else-if="!store.hasProfile && store.initializationFailed" class="boot-screen load-failed">
    <div class="brand-mark"><LeafMark /></div>
    <strong>暂时无法加载档案</strong><span>请检查连接后重试。</span>
    <button :disabled="store.busy" @click="store.initialize()">{{ store.busy ? '正在加载…' : '重新加载' }}</button>
  </div>

  <div v-else-if="!store.hasProfile" class="onboarding-shell">
    <ProfileView onboarding @saved="onboardingSaved" />
  </div>

  <div v-else class="app-shell">
    <aside class="sidebar">
      <button class="brand" aria-label="轻衡首页" @click="navigate('today')">
        <LeafMark /><strong>轻衡</strong>
      </button>
      <nav aria-label="主导航">
        <button aria-label="今日能量概览" title="今日能量概览" :aria-current="route === 'today' ? 'page' : undefined" :class="{ active: route === 'today' }" @click="navigate('today')">
          <UiIcon name="home" /><b>今日</b>
        </button>
        <button aria-label="历史记录" title="历史记录" :aria-current="route === 'records' ? 'page' : undefined" :class="{ active: route === 'records' }" @click="navigate('records')">
          <UiIcon name="record" /><b>记录</b>
        </button>
        <button aria-label="个人档案" title="个人档案" :aria-current="route === 'profile' ? 'page' : undefined" :class="{ active: route === 'profile' }" @click="navigate('profile')">
          <UiIcon name="person" /><b>档案</b>
        </button>
      </nav>
      <footer class="sidebar-footer">
        <LeafMark />
        <p>轻盈生活，<br />从每一餐开始</p>
      </footer>
    </aside>

    <section class="main-stage">
      <Transition name="page" mode="out-in">
      <div :key="route" class="route-page">
      <TodayView v-if="route === 'today'" @open-records="navigate('records')" />
      <RecordsView v-else-if="route === 'records'" />
      <ProfileView v-else />
      </div>
      </Transition>
    </section>

    <nav class="mobile-nav" aria-label="手机主导航">
      <button aria-label="今日能量概览" title="今日能量概览" :aria-current="route === 'today' ? 'page' : undefined" :class="{ active: route === 'today' }" @click="navigate('today')">
        <UiIcon name="home" /><b>今日</b>
      </button>
      <button aria-label="历史记录" title="历史记录" :aria-current="route === 'records' ? 'page' : undefined" :class="{ active: route === 'records' }" @click="navigate('records')">
        <UiIcon name="record" /><b>记录</b>
      </button>
      <button aria-label="个人档案" title="个人档案" :aria-current="route === 'profile' ? 'page' : undefined" :class="{ active: route === 'profile' }" @click="navigate('profile')">
        <UiIcon name="person" /><b>档案</b>
      </button>
    </nav>
  </div>

  <FeedbackToast />
</template>

<style scoped>
.boot-screen { display: grid; width: 100%; height: 100%; place-items: center; align-content: center; gap: 10px; color: var(--qh-muted); background: var(--qh-bg); }
.boot-screen strong { color: var(--qh-text); font-family: var(--qh-display); font-size: 27px; }
.boot-screen span { font-size: 12px; }
.brand-mark { display: grid; place-items: center; width: 58px; height: 58px; border-radius: 50%; background: var(--qh-brand); color: white; }
.load-failed button { min-height: 44px; margin-top: 8px; padding: 10px 20px; border: 0; border-radius: var(--qh-radius-pill); color: var(--qh-cream); background: var(--qh-berry); cursor: pointer; }
.onboarding-shell { width: 100%; height: 100%; overflow: auto; background: var(--qh-bg); }
.app-shell { display: grid; width: 100%; height: 100%; grid-template-columns: 176px minmax(0, 1fr); background: var(--qh-bg); }
.sidebar { display: flex; flex-direction: column; align-items: stretch; gap: 32px; min-height: 0; overflow-y: auto; padding: 30px 12px 24px; color: white; background: var(--qh-berry); }
.brand { display: flex; align-items: center; justify-content: center; gap: 8px; flex-shrink: 0; padding: 0; border: 0; color: white; background: transparent; cursor: pointer; }
.brand strong { font-family: var(--qh-display); font-size: 28px; letter-spacing: .02em; }
.brand .leaf-mark { width: 38px; height: 32px; }
.sidebar nav { display: grid; gap: 12px; }
.sidebar nav button { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 52px; padding: 8px 18px; border: 1.5px solid transparent; border-radius: var(--qh-radius-pill); color: white; background: transparent; text-align: left; cursor: pointer; }
.sidebar nav button .ui-icon { box-sizing: border-box; width: 32px; height: 32px; padding: 5px; border-radius: 50%; color: white; }
.sidebar nav button b { font-size: 17px; font-weight: 500; }
.sidebar nav button.active { color: var(--qh-berry); background: var(--qh-cream); }
.sidebar nav button.active b { font-weight: 700; }
.sidebar nav button.active .ui-icon { color: white; background: var(--qh-berry); }
.sidebar nav button:focus-visible, .brand:focus-visible { outline-color: white; }
.sidebar-footer { display: grid; justify-items: start; gap: 12px; padding: 32px 16px 0; margin-top: auto; flex-shrink: 0; }
.sidebar-footer .leaf-mark { width: 105px; height: 84px; color: white; }
.sidebar-footer p { margin: 0; font-size: 13px; line-height: 1.8; }
.main-stage { min-width: 0; height: 100%; overflow: auto; background: var(--qh-bg); }
.mobile-nav { display: none; }
@media (hover: hover) { .sidebar nav button:not(.active):hover { border-color: var(--qh-on-brand); } }
@media (max-height: 600px) { .sidebar-footer .leaf-mark { width: 64px; height: 52px; } .sidebar-footer { padding-top: 10px; } }
@media (max-width: 760px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { display: none; }
  .mobile-nav { position: fixed; z-index: 30; left: 0; right: 0; bottom: 0; display: grid; grid-template-columns: repeat(3, 1fr); height: calc(64px + env(safe-area-inset-bottom)); padding: 6px 12px calc(6px + env(safe-area-inset-bottom)); border-top: var(--qh-stroke) solid var(--qh-border-strong); background: var(--qh-card); }
  .mobile-nav button { display: grid; place-items: center; gap: 3px; border: 0; border-radius: var(--qh-radius-control); color: var(--qh-muted); background: transparent; cursor: pointer; }
  .main-stage { padding-top: env(safe-area-inset-top); scroll-padding-bottom: 100px; }
  .main-stage :deep(.profile-page), .main-stage :deep(.records-page) { padding-bottom: calc(96px + env(safe-area-inset-bottom)); }
  .mobile-nav button b { font-size: 11px; }
  .mobile-nav button.active { color: var(--qh-brand); background: var(--qh-surface-subtle); }
  .mobile-nav button .ui-icon { box-sizing: border-box; width: 30px; height: 30px; padding: 4px; border-radius: 50%; }
  .mobile-nav button.active .ui-icon { color: white; background: var(--qh-berry); }
}
</style>
