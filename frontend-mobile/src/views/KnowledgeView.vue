<template>
  <div class="knowledge-view">
    <van-nav-bar title="知识库" />

    <div class="stats-bar">
      <span>共 {{ documents.length }} 份资料</span>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="load">
      <van-list>
        <van-swipe-cell v-for="doc in documents" :key="doc.id">
          <van-cell :title="doc.title || doc.filename" :label="doc.category || '未分类'">
            <template #icon>
              <van-icon :name="fileIcon(doc.file_type)" class="doc-icon" />
            </template>
            <template #value>
              <van-tag :type="doc.status === 'ready' ? 'success' : 'warning'">
                {{ doc.status === 'ready' ? '已就绪' : '处理中' }}
              </van-tag>
            </template>
          </van-cell>
          <template #right>
            <van-button square type="danger" text="删除" @click="onDelete(doc.id)" />
          </template>
        </van-swipe-cell>

        <van-empty v-if="documents.length === 0" description="还没有资料，点击下方按钮上传" />
      </van-list>
    </van-pull-refresh>

    <van-floating-bubble icon="plus" @click="showUpload = true" />

    <van-popup v-model:show="showUpload" position="bottom" round>
      <div class="upload-panel">
        <h3>上传资料</h3>
        <van-field
          v-model="category"
          label="分类"
          placeholder="例如: 数学/英语"
        />
        <van-uploader
          :after-read="(file: any) => onUpload(file)"
          :max-count="1"
          :disabled="uploading"
          accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg"
        >
          <van-button icon="uploader" type="primary" :loading="uploading" loading-text="上传中">
            选择文件
          </van-button>
        </van-uploader>
        <p class="hint">支持 PDF / TXT / MD / DOCX / 图片（单个 ≤ 20MB）</p>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import { listDocuments, uploadDocument, deleteDocument, type DocumentItem } from '@/api/document'

const documents = ref<DocumentItem[]>([])
const refreshing = ref(false)
const showUpload = ref(false)
const category = ref('')
const uploading = ref(false)

async function load() {
  documents.value = await listDocuments()
  refreshing.value = false
}

function fileIcon(type: string): string {
  const map: Record<string, string> = {
    pdf: 'description',
    docx: 'description',
    txt: 'notes-o',
    md: 'notes-o',
    png: 'photo-o',
    jpg: 'photo-o',
    jpeg: 'photo-o',
  }
  return map[type] || 'file-o'
}

async function onUpload(file: any) {
  const f = file?.file
  if (!f) return
  if (f.size > 20 * 1024 * 1024) {
    showToast('文件过大，请小于 20MB')
    return
  }
  uploading.value = true
  try {
    await uploadDocument(f, category.value || undefined)
    showToast('上传成功，正在解析...')
    showUpload.value = false
    category.value = ''
    await load()
  } catch {
    // error toast in interceptor
  } finally {
    uploading.value = false
  }
}

async function onDelete(id: number) {
  await showConfirmDialog({ title: '确认删除', message: '删除后无法恢复' })
  await deleteDocument(id)
  showToast('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped lang="scss">
.knowledge-view {
  min-height: calc(100vh - 50px);
}

.stats-bar {
  padding: 10px 16px;
  color: var(--kg-text-secondary);
  font-size: 13px;
}

.doc-icon {
  font-size: 20px;
  margin-right: 8px;
  color: var(--kg-primary);
}

.upload-panel {
  padding: 20px;

  h3 {
    margin: 0 0 16px;
  }

  .hint {
    color: var(--kg-text-secondary);
    font-size: 12px;
    margin-top: 12px;
  }
}

:deep(.van-floating-bubble) {
  bottom: calc(80px + var(--kg-safe-bottom));
}
</style>
