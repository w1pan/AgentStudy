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
  <div v-if="!store.initialized" class="boot-screen"><div class="brand-mark">叶</div><strong>轻衡</strong><span>正在准备本地数据…</span></div>

  <div v-else-if="!store.hasProfile" class="onboarding-shell">
    <ProfileView onboarding @saved="onboardingSaved" />
  </div>

  <div v-else class="app-shell">
    <aside class="sidebar">
      <button class="brand" aria-label="轻衡首页" @click="navigate('today')"><span>叶</span><strong>轻衡</strong></button>
      <nav aria-label="主导航">
        <button :class="{ active: route === 'today' }" @click="navigate('today')"><span>今</span><b>今日</b></button>
        <button :class="{ active: route === 'records' }" @click="navigate('records')"><span>记</span><b>记录</b></button>
        <button :class="{ active: route === 'profile' }" @click="navigate('profile')"><span>我</span><b>档案</b></button>
      </nav>
      <p>本机单用户<br />数据不会公开</p>
    </aside>

    <section class="main-stage">
      <TodayView v-if="route === 'today'" />
      <RecordsView v-else-if="route === 'records'" />
      <ProfileView v-else />
    </section>

    <nav class="mobile-nav" aria-label="手机主导航">
      <button :class="{ active: route === 'today' }" @click="navigate('today')"><span>今</span><b>今日</b></button>
      <button :class="{ active: route === 'records' }" @click="navigate('records')"><span>记</span><b>记录</b></button>
      <button :class="{ active: route === 'profile' }" @click="navigate('profile')"><span>我</span><b>档案</b></button>
    </nav>
  </div>

  <button v-if="store.error" class="error-toast" @click="store.clearError"><span>{{ store.error }}</span><b>×</b></button>
</template>

<style scoped>
.boot-screen { display: grid; width: 100%; height: 100%; place-items: center; align-content: center; gap: 9px; color: var(--qh-muted); background: var(--qh-bg); }.boot-screen strong { color: var(--qh-text); font-size: 24px; }.boot-screen span { font-size: 12px; }.brand-mark, .brand > span { display: grid; place-items: center; border-radius: 16px 5px 16px 5px; color: white; background: var(--qh-green); font-weight: 900; }.brand-mark { width: 52px; height: 52px; }
.onboarding-shell { width: 100%; height: 100%; overflow: auto; background: radial-gradient(circle at 15% 10%, #edf4e8 0, transparent 30%), var(--qh-bg); }
.app-shell { display: grid; grid-template-columns: 104px minmax(0, 1fr); width: 100%; height: 100%; background: var(--qh-bg); }.sidebar { display: flex; z-index: 10; align-items: center; flex-direction: column; padding: 24px 13px; border-right: 1px solid var(--qh-border); background: rgb(255 254 249 / 88%); backdrop-filter: blur(16px); }.brand { display: grid; gap: 7px; place-items: center; border: 0; color: var(--qh-text); background: transparent; cursor: pointer; }.brand > span { width: 43px; height: 43px; }.brand > strong { font-size: 14px; }.sidebar nav { display: grid; gap: 9px; width: 100%; margin-top: 42px; }.sidebar nav button, .mobile-nav button { display: grid; place-items: center; border: 0; color: var(--qh-muted); background: transparent; cursor: pointer; }.sidebar nav button { gap: 5px; min-height: 62px; border-radius: 14px; }.sidebar nav button span, .mobile-nav button span { display: grid; place-items: center; font-size: 12px; font-weight: 900; }.sidebar nav button b, .mobile-nav button b { font-size: 11px; }.sidebar nav button.active { color: var(--qh-green-dark); background: var(--qh-sage-soft); }.sidebar > p { margin-top: auto; color: var(--qh-muted); font-size: 9px; line-height: 1.6; text-align: center; }
.main-stage { min-width: 0; height: 100%; overflow: auto; }.mobile-nav { display: none; }.error-toast { position: fixed; z-index: 80; right: 22px; bottom: 22px; display: flex; max-width: min(420px, calc(100vw - 32px)); align-items: center; gap: 15px; padding: 13px 15px; border: 1px solid #efc0b7; border-radius: 13px; color: #813c32; background: #fff2ef; box-shadow: var(--qh-shadow); cursor: pointer; }.error-toast b { font-size: 18px; }
@media (max-width: 720px) { .app-shell { grid-template-columns: 1fr; }.sidebar { display: none; }.mobile-nav { position: fixed; z-index: 30; right: 12px; bottom: 12px; left: 12px; display: grid; grid-template-columns: repeat(3, 1fr); height: 68px; padding: 7px; border: 1px solid var(--qh-border); border-radius: 19px; background: rgb(255 254 249 / 94%); box-shadow: 0 12px 35px rgb(34 47 29 / 18%); backdrop-filter: blur(16px); }.mobile-nav button { gap: 3px; border-radius: 13px; }.mobile-nav button.active { color: var(--qh-green-dark); background: var(--qh-sage-soft); }.error-toast { right: 16px; bottom: 92px; } }
</style>
