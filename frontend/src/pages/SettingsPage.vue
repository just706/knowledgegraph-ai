<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getLLMSettings,
  updateLLMSettings,
  testLLMConnection,
  type LLMSettingsView,
  type LLMTestResult,
} from '@/api/user'

const loading = ref(false)
const saving = ref(false)
const status = ref<LLMSettingsView | null>(null)

// 测试连接状态
const testing = ref(false)
const testResult = ref<LLMTestResult | null>(null)

// 临时测试（不保存）状态
const tempTesting = ref(false)
const tempResult = ref<LLMTestResult | null>(null)
const temp = reactive({
  provider: 'openai',
  api_key: '',
  base_url: '',
  model: '',
})


// 临时测试区切换厂商：自动填充预设 base_url / model
function onTempProviderChange() {
  const preset = findPreset(temp.provider)
  if (preset) {
    if (!temp.base_url) temp.base_url = preset.base_url
    if (!temp.model) temp.model = preset.model
  }
}

const form = reactive({
  provider: 'openai',
  api_key: '',
  base_url: '',
  model: '',
})

// 是否清空已保存的 key（勾选后提交会把后端 key 置空）
const clearKey = ref(false)

const modeText: Record<string, string> = {
  own: '使用你自己的 API Key（扣你的额度）',
  fallback: '使用平台兜底 Key（扣部署者额度）',
  none: '未配置，LLM 功能不可用（仅本地模式）',
}

function findPreset(id: string | null) {
  return status.value?.provider_presets?.find((p) => p.id === id) || null
}

// 切换厂商：自动填充该厂商预设的 base_url / model（用户后续可手动覆盖）
function onProviderChange() {
  const preset = findPreset(form.provider)
  if (preset) {
    if (!form.base_url) form.base_url = preset.base_url
    if (!form.model) form.model = preset.model
  }
}

async function load() {
  loading.value = true
  try {
    status.value = await getLLMSettings()
    // 仅回填 provider / base_url / model；api_key 出于安全不回显明文，仅展示脱敏预览
    form.provider = status.value.provider || 'openai'
    form.base_url = status.value.base_url || ''
    form.model = status.value.model || ''
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const payload: Record<string, string | null> = {
      provider: form.provider || null,
      base_url: form.base_url || null,
      model: form.model || null,
    }
    // 仅当用户输入了新 key，或勾选清空时，才传 api_key 字段
    if (clearKey.value) {
      payload.api_key = null
    } else if (form.api_key.trim()) {
      payload.api_key = form.api_key.trim()
    } else {
      payload.api_key = undefined as unknown as string // 不改动现有 key
    }
    status.value = await updateLLMSettings(payload)
    form.api_key = ''
    clearKey.value = false
    ElMessage.success('已保存你的 API 设置')
  } catch {
    // 拦截器已提示
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testLLMConnection()
    if (testResult.value.ok) {
      ElMessage.success('连接成功，Key 有效')
    } else {
      ElMessage.warning(testResult.value.detail)
    }
  } catch {
    // 拦截器已提示
  } finally {
    testing.value = false
  }
}

// 临时测试（不保存）：把当前 temp 字段传给后端验证，不写库
async function handleTempTest() {
  tempTesting.value = true
  tempResult.value = null
  try {
    tempResult.value = await testLLMConnection({
      provider: temp.provider || null,
      api_key: temp.api_key.trim() || null,
      base_url: temp.base_url.trim() || null,
      model: temp.model.trim() || null,
    })
    if (tempResult.value.ok) {
      ElMessage.success('连接成功：此配置有效，可以保存')
    } else {
      ElMessage.warning(tempResult.value.detail)
    }
  } catch {
    // 拦截器已提示
  } finally {
    tempTesting.value = false
  }
}

// 临时测试通过后，一键把配置搬到正式表单并保存
async function applyTempAndSave() {
  form.provider = temp.provider
  form.api_key = temp.api_key
  form.base_url = temp.base_url
  form.model = temp.model
  await handleSave()
}

onMounted(load)
</script>

<template>
  <div class="settings">
    <el-card class="settings__card">
      <template #header>API 设置（按用户计费）</template>

      <el-alert
        v-if="status"
        :title="`当前生效模式：${modeText[status.effective_mode] || status.effective_mode}`"
        :type="status.effective_mode === 'own' ? 'success' : status.effective_mode === 'fallback' ? 'warning' : 'info'"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />

      <div v-loading="loading">
        <el-form :model="form" label-width="110px" @submit.prevent="handleSave">
          <el-form-item label="厂商">
            <el-select
              v-model="form.provider"
              placeholder="选择大模型厂商"
              style="width: 100%"
              @change="onProviderChange"
            >
              <el-option
                v-for="p in (status?.provider_presets || [])"
                :key="p.id"
                :label="p.name"
                :value="p.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="API Key">
            <el-input
              v-model="form.api_key"
              type="password"
              show-password
              placeholder="填写后扣你自己的额度，如 sk-..."
              autocomplete="off"
            />
            <div class="hint">
              已保存：<span v-if="status?.api_key_masked">{{ status.api_key_masked }}</span>
              <span v-else>无</span>
              <el-checkbox v-model="clearKey" style="margin-left: 12px">
                清除已保存的 Key
              </el-checkbox>
            </div>
          </el-form-item>

          <el-form-item label="Base URL">
            <el-input
              v-model="form.base_url"
              placeholder="接入点，选择厂商后会自动填充，可手动修改"
            />
          </el-form-item>

          <el-form-item label="模型名">
            <el-input
              v-model="form.model"
              placeholder="如 deepseek-chat / claude-3-5-sonnet-latest / gemini-1.5-flash"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="saving" @click="handleSave">保存设置</el-button>
            <el-button :loading="testing" @click="handleTest">测试已保存的连接</el-button>
            <el-button @click="load">重置</el-button>
          </el-form-item>

          <el-alert
            v-if="testResult"
            :title="testResult.ok ? '连接成功：Key 有效，AI 功能已可用' : '连接失败'"
            :type="testResult.ok ? 'success' : 'error'"
            :description="testResult.detail"
            :closable="false"
            show-icon
            style="margin-bottom: 16px"
          />

          </el-form>
          </div>

          <el-divider />

          <el-collapse>
            <el-collapse-item name="temp">
              <template #title>
                <span class="temp-title">临时测试（不保存）</span>
                <span class="temp-sub">先填 Key 试连通，确认有效后再保存</span>
              </template>

              <el-form :model="temp" label-width="110px">
                <el-form-item label="厂商">
                  <el-select
                    v-model="temp.provider"
                    placeholder="选择大模型厂商"
                    style="width: 100%"
                    @change="onTempProviderChange"
                  >
                    <el-option
                      v-for="p in (status?.provider_presets || [])"
                      :key="p.id"
                      :label="p.name"
                      :value="p.id"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="API Key">
                  <el-input
                    v-model="temp.api_key"
                    type="password"
                    show-password
                    placeholder="临时输入，不会保存"
                    autocomplete="off"
                  />
                </el-form-item>
                <el-form-item label="Base URL">
                  <el-input v-model="temp.base_url" placeholder="选择厂商后自动填充，可手动改" />
                </el-form-item>
                <el-form-item label="模型名">
                  <el-input v-model="temp.model" placeholder="如 deepseek-chat" />
                </el-form-item>
                <el-form-item>
                  <el-button :loading="tempTesting" @click="handleTempTest">测试此配置</el-button>
                </el-form-item>
              </el-form>

              <el-alert
                v-if="tempResult"
                :title="tempResult.ok ? '连接成功：此配置有效，可以保存' : '连接失败'"
                :type="tempResult.ok ? 'success' : 'error'"
                :description="tempResult.detail"
                :closable="false"
                show-icon
              />
              <el-button
                v-if="tempResult?.ok"
                type="primary"
                size="small"
                style="margin-top: 10px"
                @click="applyTempAndSave"
              >填入并保存此配置</el-button>
            </el-collapse-item>
          </el-collapse>

      <el-divider />

      <p class="tip">
        说明：支持 OpenAI 及 DeepSeek、通义千问、智谱 GLM、Kimi、MiniMax、Ollama(本地)、
        Anthropic Claude、Google Gemini 等多家厂商。填写你自己的 API Key 后，出题、答疑、
        错题解析、知识图谱与思维导图等所有 AI 调用都走你的账户（按你的用量计费）。
        未填写时，系统会回退使用平台兜底 Key（扣部署者额度，可在后端关闭）。
        Key 在传输与存储时均加密，页面只展示脱敏预览。
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.settings {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 24px 0;
  min-height: 60vh;
}
.settings__card {
  width: 640px;
  max-width: 92vw;
}
.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
}
.temp-title {
  font-weight: 600;
}
.temp-sub {
  margin-left: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
