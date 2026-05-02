<script setup lang="ts">
import { computed } from 'vue'
import type { BookingCard as BookingCardType } from '@/types'

const props = defineProps<{
  card: BookingCardType
}>()

const typeConfig = computed(() => {
  switch (props.card.type) {
    case 'flight':
      return { border: 'border-l-blue-500', icon: 'plane', label: '航班' }
    case 'hotel':
      return { border: 'border-l-orange-500', icon: 'building', label: '酒店' }
    case 'car_rental':
      return { border: 'border-l-green-500', icon: 'car', label: '租车' }
    default:
      return { border: 'border-l-purple-500', icon: 'briefcase', label: '其他' }
  }
})

const d = computed(() => props.card.data)

function formatTime(t: string | undefined): string {
  if (!t) return ''
  return t.length >= 16 ? t.slice(5, 16) : t
}
</script>

<template>
  <div :class="['border-l-4 rounded-lg bg-white shadow-sm border border-gray-100 p-4 mt-3', typeConfig.border]">
    <div class="flex items-center gap-2 mb-2">
      <svg v-if="card.type === 'flight'" class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
      </svg>
      <svg v-else-if="card.type === 'hotel'" class="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11m16-11v11M8 14v.01M12 14v.01M16 14v.01M8 18v.01M12 18v.01M16 18v.01" />
      </svg>
      <svg v-else-if="card.type === 'car_rental'" class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M5 17h14M5 17a2 2 0 01-2-2V9l3-5h12l3 5v6a2 2 0 01-2 2M5 17a2 2 0 002 2h10a2 2 0 002-2" />
        <circle cx="7" cy="14" r="1" fill="currentColor" />
        <circle cx="17" cy="14" r="1" fill="currentColor" />
      </svg>
      <span :class="['text-xs font-semibold uppercase tracking-wider', {
        'text-blue-600': card.type === 'flight',
        'text-orange-600': card.type === 'hotel',
        'text-green-600': card.type === 'car_rental',
      }]">{{ typeConfig.label }}</span>
    </div>

    <template v-if="card.type === 'flight'">
      <div class="flex items-center gap-3 text-sm">
        <div class="text-right">
          <p class="font-bold text-gray-900">{{ d.departure_time ? d.departure_time.slice(11, 16) : '--:--' }}</p>
          <p class="text-gray-500 text-xs">{{ d.departure }}</p>
        </div>
        <div class="flex-1 flex flex-col items-center">
          <span class="text-xs text-gray-400">{{ d.flight_number || d.flight }}</span>
          <div class="w-full h-px bg-gray-200 relative my-1">
            <svg class="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </div>
          <span class="text-xs text-gray-400">{{ d.duration || '' }}</span>
        </div>
        <div>
          <p class="font-bold text-gray-900">{{ d.arrival_time ? d.arrival_time.slice(11, 16) : '--:--' }}</p>
          <p class="text-gray-500 text-xs">{{ d.arrival }}</p>
        </div>
      </div>
      <p v-if="d.price" class="mt-2 text-sm font-semibold text-red-500">¥{{ d.price }}</p>
    </template>

    <template v-else-if="card.type === 'hotel'">
      <p class="font-semibold text-gray-900 text-sm">{{ d.name || d.hotel_name || '酒店' }}</p>
      <p v-if="d.location || d.address" class="text-xs text-gray-500 mt-0.5">{{ d.location || d.address }}</p>
      <div v-if="d.check_in || d.check_out" class="flex gap-4 mt-2 text-xs text-gray-500">
        <span>入住: {{ d.check_in ? formatTime(d.check_in as string) : '--' }}</span>
        <span>离店: {{ d.check_out ? formatTime(d.check_out as string) : '--' }}</span>
      </div>
      <p v-if="d.price" class="mt-1 text-sm font-semibold text-red-500">¥{{ d.price }}</p>
    </template>

    <template v-else-if="card.type === 'car_rental'">
      <p class="font-semibold text-gray-900 text-sm">{{ d.name || d.car_name || '车辆' }}</p>
      <p v-if="d.location" class="text-xs text-gray-500 mt-0.5">{{ d.location }}</p>
      <div v-if="d.pickup || d.dropoff" class="flex gap-4 mt-2 text-xs text-gray-500">
        <span>取车: {{ d.pickup ? formatTime(d.pickup as string) : '--' }}</span>
        <span>还车: {{ d.dropoff ? formatTime(d.dropoff as string) : '--' }}</span>
      </div>
      <p v-if="d.price" class="mt-1 text-sm font-semibold text-red-500">¥{{ d.price }}</p>
    </template>

    <template v-else>
      <pre class="text-xs text-gray-600 whitespace-pre-wrap">{{ JSON.stringify(d, null, 2) }}</pre>
    </template>
  </div>
</template>
