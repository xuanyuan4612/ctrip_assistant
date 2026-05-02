<script setup lang="ts">
const props = defineProps<{
  label: string
  value: string | number
  icon?: string
  trend?: number
  color?: 'blue' | 'indigo' | 'green' | 'orange' | 'purple'
}>()

const colorMap: Record<string, string> = {
  blue: 'bg-blue-500',
  indigo: 'bg-indigo-500',
  green: 'bg-green-500',
  orange: 'bg-orange-500',
  purple: 'bg-purple-500',
}

const iconMap: Record<string, string> = {
  users: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  chat: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  token: 'M13 10V3L4 14h7v7l9-11h-7z',
  cost: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  activity: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
}

const iconBg = colorMap[props.color || 'blue'] || 'bg-blue-500'
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-start gap-4 hover:shadow-md transition-shadow">
    <div :class="['w-11 h-11 rounded-lg flex items-center justify-center shrink-0', iconBg]">
      <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path :d="iconMap[props.icon || 'users'] || iconMap.users" />
      </svg>
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-sm text-gray-500 truncate">{{ label }}</p>
      <div class="flex items-baseline gap-2 mt-1">
        <p class="text-2xl font-bold text-gray-900">{{ value }}</p>
        <span v-if="trend !== undefined" :class="['text-xs font-medium', trend >= 0 ? 'text-green-600' : 'text-red-600']">
          {{ trend >= 0 ? '+' : '' }}{{ trend }}%
        </span>
      </div>
    </div>
  </div>
</template>
