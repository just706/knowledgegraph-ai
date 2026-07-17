<template>
  <div class="register-page">
    <van-nav-bar title="注册" left-text="返回" left-arrow @click-left="goBack" />

    <div class="form-wrap">
      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="email"
            label="邮箱"
            placeholder="请输入邮箱"
            :rules="[{ required: true, message: '请填写邮箱' }]"
          />
          <van-field
            v-model="password"
            type="password"
            label="密码"
            placeholder="至少8位"
            :rules="[{ required: true, message: '请填写密码' }, { validator: (val: string) => val.length >= 8, message: '密码至少8位' }]"
          />
          <van-field
            v-model="displayName"
            label="昵称"
            placeholder="选填"
          />
        </van-cell-group>

        <div class="actions">
          <van-button round block type="primary" native-type="submit" :loading="loading">
            注册并登录
          </van-button>
        </div>
      </van-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const displayName = ref('')
const loading = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    await auth.register(email.value, password.value, displayName.value || undefined)
    showToast('注册成功')
    router.replace('/chat')
  } catch {
    // 错误已在拦截器中 toast
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.back()
}
</script>

<style scoped lang="scss">
.register-page {
  min-height: 100vh;
}

.form-wrap {
  padding-top: 40px;
}

.actions {
  margin-top: 32px;
  padding: 0 16px;
}
</style>
