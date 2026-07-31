<script setup lang="ts">
import ChatInterface from './components/ChatInterface.vue'
</script>

<template>
  <ChatInterface />
</template>

<style>
/* 全局重置，确保聊天应用占满全屏 */
html, body, #app {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
