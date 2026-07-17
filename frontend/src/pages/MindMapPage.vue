<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMindmap, type MindNode, type MindmapData } from '@/api/mindmap'

const router = useRouter()
const data = ref<MindmapData | null>(null)
const loading = ref(false)
const category = ref('全部')
const categoryOptions = ['全部', '数学', '语文', '英语', '物理', '化学', '生物', '历史', '政治', '计算机', '未分类']

// 可折叠状态：以实体 id 或路径名为 key，记录是否展开
const collapsed = ref<Set<string>>(new Set())
// 当前选中的节点
const selectedId = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    data.value = await getMindmap(category.value === '全部' ? undefined : category.value)
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

function nodeKey(n: MindNode, path: string): string {
  return n.entity_id != null ? `e${n.entity_id}` : `${path}/${n.name}`
}

function isCollapsed(n: MindNode, path: string): boolean {
  return collapsed.value.has(nodeKey(n, path))
}

function toggle(n: MindNode, path: string) {
  const k = nodeKey(n, path)
  const s = new Set(collapsed.value)
  if (s.has(k)) s.delete(k)
  else s.add(k)
  collapsed.value = s
}

function selectLeaf(n: MindNode) {
  if (n.kind !== 'leaf' || n.entity_id == null) return
  selectedId.value = n.entity_id
  // 跳转到 AI 问答，并预填关于该概念的问题
  router.push({
    name: 'chat',
    query: { q: `请讲解「${n.name}」这个概念，并举个例子帮助理解。` },
  })
}

const isEmpty = computed(() => data.value && data.value.root.children.length === 0)

onMounted(load)
</script>

<template>
  <div class="mindmap-page">
    <div class="header">
      <div>
        <h2>思维导图</h2>
        <p class="sub">基于你的知识库自动生成的学习地图，点击节点可层层展开。</p>
      </div>
      <div class="actions">
        <el-select v-model="category" style="width: 120px" @change="load">
          <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
        </el-select>
        <el-tag v-if="data" :type="data.mode === 'llm' ? 'success' : 'info'" size="small">
          {{ data.mode === 'llm' ? 'AI 语义编排' : '本地自动编排' }}
        </el-tag>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert
      v-if="data && data.mode === 'local'"
      class="tip"
      title="当前为本地演示模式：思维导图由图算法自动分层生成。配置 LLM 密钥后将升级为 AI 语义编排的学习路径。"
      type="info"
      :closable="false"
      show-icon
    />

    <div v-loading="loading" class="tree-wrap">
      <el-empty v-if="isEmpty" description="还没有可生成思维导图的内容，请先到「知识库」上传资料" />

      <div v-else-if="data" class="tree">
        <TreeNode
          :node="data.root"
          :path="'root'"
          :depth="0"
          :collapsed="collapsed"
          :selected-id="selectedId"
          @toggle="toggle"
          @select="selectLeaf"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// 递归树节点组件（与父组件同文件，便于折叠交互）
import { defineComponent, h } from 'vue'
import type { PropType } from 'vue'

const TreeNode = defineComponent({
  name: 'TreeNode',
  props: {
    node: { type: Object as PropType<MindNode>, required: true },
    path: { type: String, required: true },
    depth: { type: Number, default: 0 },
    collapsed: { type: Object as PropType<Set<string>>, required: true },
    selectedId: { type: Number as PropType<number | null>, default: null },
  },
  emits: ['toggle', 'select'],
  computed: {
    key(): string {
      return this.node.entity_id != null ? `e${this.node.entity_id}` : `${this.path}/${this.node.name}`
    },
    closed(): boolean {
      return this.collapsed.has(this.key)
    },
    isLeaf(): boolean {
      return this.node.kind === 'leaf' || this.node.children.length === 0
    },
    isSelected(): boolean {
      return this.node.entity_id != null && this.node.entity_id === this.selectedId
    },
  },
  methods: {
    onClick() {
      if (this.isLeaf) {
        this.$emit('select', this.node)
      } else {
        this.$emit('toggle', this.node, this.path)
      }
    },
  },
  render() {
    const n = this.node
    const hasChildren = n.children.length > 0
    const indent = { paddingLeft: `${this.depth * 22}px` }

    const caret = !this.isLeaf
      ? h('span', { class: 'caret', onClick: (e: Event) => { e.stopPropagation(); this.$emit('toggle', n, this.path) } },
          this.closed ? '▸' : '▾')
      : h('span', { class: 'caret placeholder' }, '•')

    const labelClass = [
      'node-label',
      `kind-${n.kind}`,
      this.isSelected ? 'selected' : '',
      this.isLeaf ? 'leaf' : 'branch',
    ].join(' ')

    const meta = n.meta && n.meta.mentions ? ` (${n.meta.mentions})` : ''

    const row = h('div', {
      class: labelClass,
      style: indent,
      onClick: this.onClick,
    }, [
      caret,
      h('span', { class: 'node-text' }, n.name + meta),
      this.isLeaf
        ? h('span', { class: 'go', title: '点击向 AI 提问' }, '→')
        : null,
    ])

    const childrenVNodes = (!this.closed && hasChildren)
      ? n.children.map((c) =>
          h(TreeNode, {
            key: c.entity_id != null ? `e${c.entity_id}` : `${this.key}/${c.name}`,
            node: c,
            path: this.key,
            depth: this.depth + 1,
            collapsed: this.collapsed,
            selectedId: this.selectedId,
            onToggle: (node: MindNode, p: string) => this.$emit('toggle', node, p),
            onSelect: (node: MindNode) => this.$emit('select', node),
          }),
        )
      : []

    return h('div', { class: 'tree-node' }, [row, ...childrenVNodes])
  },
})

export default { components: { TreeNode } }
</script>

<style scoped>
.mindmap-page {
  padding: 20px 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 12px;
}
.header h2 { margin: 0; font-size: 20px; }
.sub { margin: 4px 0 0; color: #909399; font-size: 13px; }
.actions { display: flex; align-items: center; gap: 10px; }
.tip { margin-bottom: 12px; }
.tree-wrap {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}
.tree-node { line-height: 1.4; }
.node-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 14px;
}
.node-label:hover { background: #f0f5ff; }
.node-label.kind-root { font-size: 16px; font-weight: 700; color: #303133; }
.node-label.branch { font-weight: 600; color: #409eff; }
.node-label.leaf { color: #606266; font-weight: 400; }
.node-label.selected { background: #ecf5ff; outline: 1px solid #409eff; }
.caret { width: 14px; text-align: center; color: #909399; user-select: none; }
.caret.placeholder { color: #c0c4cc; }
.node-text { flex: 1; }
.go { color: #67c23a; font-weight: 700; }
</style>
