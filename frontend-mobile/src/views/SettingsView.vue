<template>
  <div class="settings-view">
    <van-nav-bar title="API 设置" left-text="返回" left-arrow @click-left="goBack" />

    <van-cell-group inset title="LLM 配置">
      <van-field
        v-model="provider"
        label="厂商"
        readonly
        is-link
        @click="showProvider = true"
      />
      <van-field
        v-model="apiKey"
        label="API Key"
        placeholder="选填，留空用全局兜底"
        type="password"
      />
      <van-field
        v-model="baseUrl"
        label="Base URL"
        placeholder="选填"
      />
      <van-field
        v-model="model"
        label="模型"
        placeholder="选填，如 gpt-4o-mini"
      />
    </van-cell-group>

    <div class="actions">
      <van-button round block type="primary" :loading="saving" @click="save">保存</van-button>
      <van-button round block plain type="primary" :loading="testing" @click="test">测试连接</van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, showFailToast } from 'vant'
import {
  getLLMSettings, updateLLMSettings, testLLMConnection,
  type ProviderPreset,
} from '@/api/user'

const router = useRouter()
const provider = ref('')
const apiKey = ref('')
const baseUrl = ref('')
const model = ref('')
const presets = ref<ProviderPreset[]>([])
const showProvider = ref(false)
const saving = ref(false)
const testing = ref(false)

async function load() {
  const settings = await getLLMSettings()
  provider.value = settings.provider || ''
  apiKey.value = settings.api_key_masked ? '' : ''
  baseUrl.value = settings.base_url || ''
  model.value = settings.model || ''
  presets.value = settings.provider_presets || []
}

async function save() {
  saving.value = true
  try {
    await updateLLMSettings({
      provider: provider.value || null,
      api_key: apiKey.value || null,
      base_url: baseUrl.value || null,
      model: model.value || null,
    })
    showToast('已保存')
  } catch {
    // error toast
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  try {
    const res = await testLLMConnection({
      provider: provider.value || undefined,
      api_key: apiKey.value || undefined,
      base_url: baseUrl.value || undefined,
      model: model.value || undefined,
    })
    if (res.ok) showSuccessToast('连接成功')
    else showFailToast(res.detail)
  } catch {
    // error toast
  } finally {
    testing.value = false
  }
}

function goBack() {
  router.back()
}

onMounted(load)
</script>

<style scoped lang="scss">
.settings-view {
  min-height: calc(100vh - 50px);
}

.actions {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
