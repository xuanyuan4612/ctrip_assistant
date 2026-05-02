<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const tab = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  if (tab.value === 'register' && password.value !== confirmPassword.value) {
    error.value = '两次密码输入不一致'
    return
  }
  if (tab.value === 'register' && password.value.length < 6) {
    error.value = '密码至少6位'
    return
  }

  loading.value = true
  try {
    let success: boolean
    if (tab.value === 'login') {
      success = await auth.loginAction(username.value, password.value)
    } else {
      success = await auth.registerAction(username.value, password.value)
    }
    if (success) {
      router.push('/')
    } else {
      error.value = tab.value === 'login' ? '登录失败，请检查用户名和密码' : '注册失败，用户名可能已存在'
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-primary-50 via-white to-indigo-50 flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-indigo-600 shadow-lg mb-4">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
            <path d="M12 2a4 4 0 014 4v2a4 4 0 01-8 0V6a4 4 0 014-4z" />
            <path d="M16 14H8a4 4 0 00-4 4v2a2 2 0 002 2h12a2 2 0 002-2v-2a4 4 0 00-4-4z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">携程 AI 助手</h1>
        <p class="text-sm text-gray-500 mt-1">智能旅行服务系统</p>
      </div>

      <!-- Card -->
      <div class="bg-white rounded-2xl shadow-xl border border-gray-100 p-6">
        <!-- Tabs -->
        <div class="flex bg-gray-100 rounded-lg p-1 mb-6">
          <button
            class="flex-1 py-2 text-sm font-medium rounded-md transition-all"
            :class="tab === 'login' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="tab = 'login'; error = ''"
          >登录</button>
          <button
            class="flex-1 py-2 text-sm font-medium rounded-md transition-all"
            :class="tab === 'register' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="tab = 'register'; error = ''"
          >注册</button>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              v-model="username"
              type="text"
              class="input-field"
              placeholder="请输入用户名"
              autocomplete="username"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              v-model="password"
              type="password"
              class="input-field"
              placeholder="请输入密码"
              autocomplete="current-password"
            />
          </div>
          <div v-if="tab === 'register'">
            <label class="block text-sm font-medium text-gray-700 mb-1">确认密码</label>
            <input
              v-model="confirmPassword"
              type="password"
              class="input-field"
              placeholder="请再次输入密码"
            />
          </div>

          <!-- Error -->
          <div v-if="error" class="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{{ error }}</div>

          <!-- Submit -->
          <button
            type="submit"
            class="btn-primary w-full text-center disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading"
          >
            <span v-if="loading" class="inline-flex items-center gap-2">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              处理中...
            </span>
            <span v-else>{{ tab === 'login' ? '登录' : '注册' }}</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
