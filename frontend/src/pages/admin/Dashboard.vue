<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { healthCheck } from '@/api/client'
import type { AdminStats } from '@/types'
import StatsCard from '@/components/admin/StatsCard.vue'

const stats = ref<AdminStats>({
  totalUsers: 0,
  totalConversations: 0,
  totalTokens: 0,
  totalCost: 0,
  activeToday: 0,
})

const healthOk = ref(false)
const loading = ref(true)

onMounted(async () => {
  healthOk.value = await healthCheck()
  // Placeholder: In production, fetch from /api/v1/admin/stats
  stats.value = {
    totalUsers: 128,
    totalConversations: 1567,
    totalTokens: 892345,
    totalCost: 123.45,
    activeToday: 37,
  }
  loading.value = false
})
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">仪表盘</h1>
        <p class="text-sm text-gray-500 mt-1">系统运行概览</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full" :class="healthOk ? 'bg-green-500' : 'bg-red-500'"></span>
        <span class="text-sm text-gray-500">服务 {{ healthOk ? '正常运行' : '异常' }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <svg class="w-8 h-8 animate-spin text-primary-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <!-- Stats Grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
      <StatsCard label="总用户数" :value="stats.totalUsers" icon="users" color="blue" :trend="12" />
      <StatsCard label="总对话数" :value="stats.totalConversations" icon="chat" color="indigo" :trend="8" />
      <StatsCard label="总 Token 数" :value="stats.totalTokens.toLocaleString()" icon="token" color="purple" :trend="15" />
      <StatsCard label="总成本 ($)" :value="stats.totalCost.toFixed(2)" icon="cost" color="orange" :trend="-3" />
      <StatsCard label="今日活跃" :value="stats.activeToday" icon="activity" color="green" :trend="5" />
    </div>

    <!-- Placeholder charts area -->
    <div class="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="card p-6">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">对话趋势</h3>
        <div class="h-48 flex items-center justify-center text-gray-400 text-sm bg-gray-50 rounded-lg">
          图表区域（待接入）
        </div>
      </div>
      <div class="card p-6">
        <h3 class="text-sm font-semibold text-gray-900 mb-4">Token 消耗</h3>
        <div class="h-48 flex items-center justify-center text-gray-400 text-sm bg-gray-50 rounded-lg">
          图表区域（待接入）
        </div>
      </div>
    </div>
  </div>
</template>
