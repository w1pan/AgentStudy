<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import UiIcon from '@/components/UiIcon.vue'
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
  <div v-if="!store.initialized" class="boot-screen">
    <div class="brand-mark"><i /></div>
    <strong>轻衡</strong><span>正在整理今天的能量账本…</span>
  </div>

  <div v-else-if="!store.hasProfile" class="onboarding-shell">
    <ProfileView onboarding @saved="onboardingSaved" />
  </div>

  <div v-else class="app-shell">
    <aside class="sidebar">
      <button class="brand" aria-label="轻衡首页" @click="navigate('today')">
        <UiIcon name="leaf" /><strong>轻衡</strong>
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
      <div class="sidebar-botanical" aria-hidden="true"><svg viewBox="0 0 100 130"><path d="M10 130Q18 65 70 10" fill="none" stroke="#a9b585" stroke-width="2"/><path d="M24 90Q0 72 12 44Q35 61 24 90M40 61Q36 23 73 10Q72 43 40 61M17 116Q30 74 64 73Q56 110 17 116" fill="#a4b276"/><ellipse cx="15" cy="136" rx="52" ry="28" fill="#f9d1cb"/></svg></div>
      <p>轻盈生活<br />从每一餐开始</p>
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

  <button v-if="store.error" class="error-toast" @click="store.clearError">
    <span>{{ store.error }}</span
    ><b>×</b>
  </button>
</template>

<style scoped>
.boot-screen {
  display: grid;
  width: 100%;
  height: 100%;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: var(--qh-muted);
  background: radial-gradient(circle at 50% 45%, #fff 0, transparent 28%), var(--qh-bg);
}
.boot-screen strong {
  color: var(--qh-text);
  font-family: var(--qh-display);
  font-size: 27px;
}
.boot-screen span {
  font-size: 12px;
}
.brand-mark,
.brand > span {
  position: relative;
  display: grid;
  place-items: center;
  border: 1px solid rgb(185 227 199 / 28%);
  border-radius: 50%;
  color: white;
  background: var(--qh-brand);
}
.brand-mark {
  width: 54px;
  height: 54px;
}
.brand-mark i,
.brand > span i {
  width: 46%;
  height: 1px;
  background: var(--qh-mint);
  transform: rotate(-8deg);
}
.brand-mark i::before,
.brand > span i::before,
.brand-mark i::after,
.brand > span i::after {
  position: absolute;
  width: 4px;
  height: 4px;
  border: 1px solid var(--qh-mint);
  border-radius: 50%;
  content: '';
}
.brand-mark i::before,
.brand > span i::before {
  left: 17%;
  transform: translateY(-50%);
}
.brand-mark i::after,
.brand > span i::after {
  right: 17%;
  transform: translateY(-50%);
}
.onboarding-shell {
  width: 100%;
  height: 100%;
  overflow: auto;
  background: radial-gradient(circle at 12% 8%, #fff 0, transparent 26%), var(--qh-bg);
}
.app-shell {
  display: grid;
  width: 100%;
  height: 100%;
  background: var(--qh-bg);
  grid-template-columns: 168px minmax(0, 1fr);
}
.sidebar {
  position: relative;
  overflow: hidden;
  display: flex;
  z-index: 10;
  align-items: center;
  flex-direction: column;
  color: #eef7f0;
  box-shadow: 8px 0 30px rgb(18 56 42 / 9%);
  background: linear-gradient(155deg, #3a001d, #571333 65%, #3a001d);
  padding: 30px 12px 22px;
}
.brand {
  place-items: center;
  border: 0;
  color: white;
  background: transparent;
  cursor: pointer;
  display: flex;
  gap: 10px;
}
.brand > span {
  width: 48px;
  height: 48px;
  background: rgb(255 255 255 / 5%);
}
.brand > strong {
  margin-top: 2px;
  font-family: var(--qh-display);
  letter-spacing: 0.12em;
  font-size: 24px;
}
.brand > small {
  color: #dfbfc9;
  font-family: var(--qh-data);
  font-size: 7px;
  letter-spacing: 0.2em;
}
.sidebar nav {
  display: grid;
  gap: 9px;
  width: 100%;
  margin-top: 44px;
}
.sidebar nav button,
.mobile-nav button {
  display: grid;
  place-items: center;
  border: 0;
  color: #dfbfc9;
  background: transparent;
  cursor: pointer;
}
.sidebar nav button {
  position: relative;
  display: flex;
  justify-content: flex-start;
  gap: 14px;
  padding: 0 20px;
  min-height: 52px;
  border-radius: 18px;
}
.sidebar nav button::before {
  position: absolute;
  left: 0;
  width: 4px;
  height: 0;
  border-radius: 2px;
  background: var(--qh-orange);
  content: '';
  transition: height 180ms ease;
}
.sidebar nav button span,
.mobile-nav button span {
  display: grid;
  place-items: center;
  font-family: var(--qh-display);
  font-size: 15px;
  font-weight: 800;
}
.sidebar nav button b,
.mobile-nav button b {
  font-size: 10px;
}
.sidebar nav button.active {
  color: var(--qh-text);
  background: var(--qh-brand-soft);
}
.sidebar nav button.active::before {
  height: 34px;
  display: none;
}
.sidebar > p {
  position: relative;
  z-index: 1;
  padding-left: 40px;
  margin-top: auto;
  color: #dfbfc9;
  line-height: 1.7;
  text-align: center;
  font-size: 11px;
}
.sidebar-botanical { position: absolute; bottom: 0; left: 0; width: 85px; pointer-events: none; }
.sidebar > p span {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 3px;
  border-radius: 50%;
  background: var(--qh-mint);
  box-shadow: 0 0 0 3px rgb(185 227 199 / 9%);
}
.main-stage {
  min-width: 0;
  height: 100%;
  overflow: auto;
  background: var(--qh-bg);
}
.mobile-nav {
  display: none;
}
.error-toast {
  position: fixed;
  z-index: 80;
  right: 22px;
  bottom: 22px;
  display: flex;
  max-width: min(420px, calc(100vw - 32px));
  align-items: center;
  gap: 15px;
  padding: 13px 15px;
  border: 1px solid #efc0b7;
  border-radius: 13px;
  color: #813c32;
  background: #fff2ef;
  box-shadow: var(--qh-shadow);
  cursor: pointer;
}
.error-toast b {
  font-size: 18px;
}
.sidebar nav button b {
  font-size: 17px;
  font-weight: 500;
}
@media (max-width: 720px) {
  .app-shell {
    grid-template-columns: 1fr;
  }
  .sidebar {
    display: none;
  }
  .mobile-nav {
    position: fixed;
    z-index: 30;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    border: 1px solid rgb(255 255 255 / 12%);
    backdrop-filter: blur(16px);
    left: 0;
    right: 0;
    bottom: 0;
    height: calc(64px + env(safe-area-inset-bottom));
    padding: 6px 12px calc(6px + env(safe-area-inset-bottom));
    border-radius: 0;
    background: #fffcf8;
    border-top: 1px solid var(--qh-border);
    box-shadow: 0 -4px 20px #3a001d05;
  }
  .mobile-nav button {
    gap: 3px;
    border-radius: 14px 6px 14px 6px;
    color: var(--qh-muted);
  }
  .mobile-nav button.active {
    color: var(--qh-brand);
    background: transparent;
  }
  .mobile-nav button.active span {
    color: var(--qh-mint);
  }
  .error-toast {
    right: 16px;
    bottom: calc(92px + env(safe-area-inset-bottom));
  }
}
</style>
