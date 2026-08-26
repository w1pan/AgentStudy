<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import ProfileView from '@/views/ProfileView.vue'
import RecordsView from '@/views/RecordsView.vue'
import TodayView from '@/views/TodayView.vue'
import { useQinghengStore } from '@/stores/qingheng'

type RouteName = 'today' | 'records' | 'profile'

const store = useQinghengStore()
const route = ref<RouteName>('today')

function readHash() {
  const value = window.location.hash.replace('#/', '')
  route.value = value === 'records' || value === 'profile' ? value : 'today'
}

function navigate(value: RouteName) {
  window.location.hash = `/${value}`
}

function onboardingSaved() {
  navigate('today')
}

onMounted(async () => {
  readHash()
  window.addEventListener('hashchange', readHash)
  await store.initialize()
})
onBeforeUnmount(() => window.removeEventListener('hashchange', readHash))
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
        <span><i /></span><strong>轻衡</strong><small>QINGHENG</small>
      </button>
      <nav aria-label="主导航">
        <button :class="{ active: route === 'today' }" @click="navigate('today')">
          <span>今</span><b>今日</b>
        </button>
        <button :class="{ active: route === 'records' }" @click="navigate('records')">
          <span>记</span><b>记录</b>
        </button>
        <button :class="{ active: route === 'profile' }" @click="navigate('profile')">
          <span>我</span><b>档案</b>
        </button>
      </nav>
      <p><span /> 本地模式<br />数据只留在这里</p>
    </aside>

    <section class="main-stage">
      <TodayView v-if="route === 'today'" />
      <RecordsView v-else-if="route === 'records'" />
      <ProfileView v-else />
    </section>

    <nav class="mobile-nav" aria-label="手机主导航">
      <button :class="{ active: route === 'today' }" @click="navigate('today')">
        <span>今</span><b>今日</b>
      </button>
      <button :class="{ active: route === 'records' }" @click="navigate('records')">
        <span>记</span><b>记录</b>
      </button>
      <button :class="{ active: route === 'profile' }" @click="navigate('profile')">
        <span>我</span><b>档案</b>
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
  background: var(--qh-green-ink);
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
  grid-template-columns: 112px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  background: var(--qh-bg);
}
.sidebar {
  display: flex;
  z-index: 10;
  align-items: center;
  flex-direction: column;
  padding: 23px 12px 18px;
  color: #eef7f0;
  background: var(--qh-green-ink);
  box-shadow: 8px 0 30px rgb(18 56 42 / 9%);
}
.brand {
  display: grid;
  gap: 6px;
  place-items: center;
  border: 0;
  color: white;
  background: transparent;
  cursor: pointer;
}
.brand > span {
  width: 48px;
  height: 48px;
  background: rgb(255 255 255 / 5%);
}
.brand > strong {
  margin-top: 2px;
  font-family: var(--qh-display);
  font-size: 16px;
  letter-spacing: 0.12em;
}
.brand > small {
  color: #92b5a1;
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
  color: #92b5a1;
  background: transparent;
  cursor: pointer;
}
.sidebar nav button {
  position: relative;
  gap: 5px;
  min-height: 66px;
  border-radius: 18px 7px 18px 7px;
}
.sidebar nav button::before {
  position: absolute;
  left: 0;
  width: 2px;
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
  color: white;
  background: rgb(255 255 255 / 8%);
}
.sidebar nav button.active::before {
  height: 26px;
}
.sidebar > p {
  margin-top: auto;
  color: #84a792;
  font-size: 9px;
  line-height: 1.7;
  text-align: center;
}
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
  background-image:
    linear-gradient(rgb(18 56 42 / 2.4%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(18 56 42 / 2.4%) 1px, transparent 1px);
  background-size: 32px 32px;
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
    right: 12px;
    bottom: 12px;
    left: 12px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    height: 68px;
    padding: 7px;
    border: 1px solid rgb(255 255 255 / 12%);
    border-radius: 20px 8px 20px 8px;
    background: rgb(18 56 42 / 96%);
    box-shadow: 0 18px 40px rgb(18 56 42 / 28%);
    backdrop-filter: blur(16px);
  }
  .mobile-nav button {
    gap: 3px;
    border-radius: 14px 6px 14px 6px;
  }
  .mobile-nav button.active {
    color: white;
    background: rgb(255 255 255 / 10%);
  }
  .mobile-nav button.active span {
    color: var(--qh-mint);
  }
  .error-toast {
    right: 16px;
    bottom: 92px;
  }
}
</style>
