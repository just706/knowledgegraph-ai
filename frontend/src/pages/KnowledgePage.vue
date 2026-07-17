<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  uploadDocument,
  listDocuments,
  getDocument,
  deleteDocument,
  type DocumentItem,
  type DocumentDetail,
} from '@/api/document'

const router = useRouter()

const documents = ref<DocumentItem[]>([])
const loading = ref(false)
const uploading = ref(false)
const drawerVisible = ref(false)
const currentDetail = ref<DocumentDetail | null>(null)
const uploadCategory = ref('未分类')

const fileTypes = '.txt,.md,.markdown,.pdf'

// 分类下拉选项（含"未分类"，及自动推断用的学科）
const categoryOptions = [
  '未分类', '数学', '语文', '英语', '物理', '化学', '生物', '历史', '政治', '计算机',
]

async function fetchDocuments() {
  loading.value = true
  try {
    documents.value = await listDocuments()
  } finally {
    loading.value = false
  }
}

async function handleUpload(options: { file: File }) {
  const file = options.file
  if (!file) return
  uploading.value = true
  try {
    const doc = await uploadDocument(file, uploadCategory.value === '未分类' ? undefined : uploadCategory.value)
    if (doc.graph_status === 'failed') {
      ElMessage.warning(
        `「${file.name}」上传并解析成功，但知识图谱构建失败：${doc.graph_error || '未知错误'}。可前往「知识图谱」页手动重新构建。`,
      )
    } else {
      ElMessage.success(`「${file.name}」上传成功（分类：${doc.category}），知识图谱已自动构建`)
    }
    await fetchDocuments()
  } catch {
    // 错误已由拦截器统一提示
  } finally {
    uploading.value = false
  }
}

async function handleDelete(item: DocumentItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${item.title}」？相关切片将一并删除。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  await deleteDocument(item.id)
  ElMessage.success('已删除')
  await fetchDocuments()
}

async function openDetail(item: DocumentItem) {
  currentDetail.value = await getDocument(item.id)
  drawerVisible.value = true
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function goPractice(item: DocumentItem) {
  router.push({ name: 'quiz', query: { subject: item.title } })
}

onMounted(fetchDocuments)
</script>

<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div>
        <h2>知识库</h2>
        <p class="subtitle">上传学习资料，系统自动解析并切片，为后续 AI 问答与知识图谱做准备。</p>
      </div>
      <el-upload
        :show-file-list="false"
        :auto-upload="true"
        :http-request="handleUpload"
        :accept="fileTypes"
        :disabled="uploading"
      >
        <el-button type="primary" :loading="uploading">
          {{ uploading ? '解析中…' : '上传资料' }}
        </el-button>
      </el-upload>
      <el-select v-model="uploadCategory" style="width: 130px; margin-left: 10px">
        <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="documents" empty-text="还没有资料，点击右上角上传" style="width: 100%">
      <el-table-column prop="title" label="标题" min-width="180" />
      <el-table-column prop="file_type" label="类型" width="90" />
      <el-table-column label="分类" width="90">
        <template #default="{ row }">
          <el-tag :type="row.category === '未分类' ? 'info' : 'primary'" size="small">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="110">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="切片数" width="90" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ready' ? 'success' : 'warning'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="图谱" width="110">
        <template #default="{ row }">
          <el-tag
            v-if="row.graph_status === 'success'"
            type="success"
          >已构建</el-tag>
          <el-tag
            v-else-if="row.graph_status === 'failed'"
            type="danger"
          >构建失败</el-tag>
          <el-tag v-else type="info">待构建</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="上传时间" min-width="170">
        <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          <el-button link type="success" @click="goPractice(row)">进入练习</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawerVisible" title="文档切片详情" size="50%">
      <div v-if="currentDetail">
        <p class="detail-meta">
          共 {{ currentDetail.chunk_count }} 个切片 · 类型 {{ currentDetail.file_type }}
        </p>
        <el-collapse>
          <el-collapse-item
            v-for="chunk in currentDetail.chunks"
            :key="chunk.id"
            :title="`第 ${chunk.chunk_index + 1} 段 · 约 ${chunk.token_estimate} tokens`"
          >
            <p class="chunk-content">{{ chunk.content }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.subtitle {
  color: #888;
  margin: 4px 0 0;
  font-size: 13px;
}
.detail-meta {
  color: #666;
  font-size: 13px;
  margin-bottom: 12px;
}
.chunk-content {
  white-space: pre-wrap;
  line-height: 1.7;
}
</style>
