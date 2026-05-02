<script setup lang="ts">
</script>

<template>
  <div class="flex items-center gap-1.5 px-4 py-3">
    <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
    <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
    <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
  </div>
</template>

<style scoped>
.animate-bounce {
  animation: loading-bounce 1.2s infinite ease-in-out;
}
@keyframes loading-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
