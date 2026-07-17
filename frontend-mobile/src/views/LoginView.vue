<template>
  <div class="login-page">
    <div class="logo">📚</div>
    <h1 class="title">知识图谱 AI</h1>
    <p class="subtitle">智能学习助手</p>

    <van-form @submit="onSubmit">
      <van-cell-group inset>
        <van-field
          v-model="email"
          name="email"
          label="邮箱"
          placeholder="请输入邮箱"
          :rules="[{ required: true, message: '请填写邮箱' }]"
        />
        <van-field
          v-model="password"
          type="password"
          name="password"
          label="密码"
          placeholder="请输入密码"
          :rules="[{ required: true, message: '请填写密码' }]"
        />
      </van-cell-group>

      <div class="actions">
        <van-button round block type="primary" native-type="submit" :loading="loading">
          登录
        </van-button>
        <van-button round block plain type="primary" @click="goRegister">
          注册新账号
        </van-button>
      </div>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    showToast('登录成功')
    const redirect = route.query.redirect as string || '/chat'
    router.replace(redirect)
  } catch {
    // 错误已在 request 拦截器中 toast
  } finally {
    loading.value = false
  }
}

function goRegister() {
  router.push({ name: 'register' })
}
</script>

<style scoped lang="scss">
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 20px 40px;
  min-height: 100vh;
}

.logo {
  font-size: 64px;
  margin-bottom: 16px;
}

.title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.subtitle {
  color: var(--kg-text-secondary);
  margin: 8px 0 40px;
}

.actions {
  width: 100%;
  margin-top: 32px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
