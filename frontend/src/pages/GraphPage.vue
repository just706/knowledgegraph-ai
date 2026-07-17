<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataSet } from 'vis-data'
import { Network } from 'vis-network'
import {
  getGraph,
  buildGraph,
  clearGraph,
  getRelationTypes,
  createRelation,
  deleteRelation,
  type GraphData,
  type GraphNode,
  type GraphEdge,
} from '@/api/graph'

const graphData = ref<GraphData | null>(null)
const loading = ref(false)
const building = ref(false)
const search = ref('')
const minWeight = ref(1)
const category = ref('全部')
const categoryOptions = ['全部', '数学', '语文', '英语', '物理', '化学', '生物', '历史', '政治', '计算机', '未分类']

// 手动关联相关状态
const linkMode = ref(false) // 是否处于"关联模式"
const linkSource = ref<GraphNode | null>(null) // 已选的第一个实体
const relationTypes = ref<string[]>([])
const relDialogVisible = ref(false)
const pickedRelation = ref('')
const linking = ref(false)

let network: Network | null = null
let nodesDs: DataSet<any> | null = null
let edgesDs: DataSet<any> | null = null
const containerRef = ref<HTMLElement | null>(null)

// 按标签着色
const LABEL_COLORS: Record<string, string> = {
  概念: '#5B8FF9',
  方法: '#61DDAA',
  结构: '#F6BD16',
  术语: '#7262FD',
  人物: '#ff9845',
  其他: '#bfbfbf',
}

const isEmpty = computed(() => graphData.value && graphData.value.nodes.length === 0)

async function loadGraph() {
  loading.value = true
  try {
    const data = await getGraph(minWeight.value, category.value === '全部' ? undefined : category.value)
    graphData.value = data
    renderGraph(data)
  } catch {
    // 错误已由拦截器提示
  } finally {
    loading.value = false
  }
}

function renderGraph(data: GraphData) {
  if (!containerRef.value) return
  const nodes = data.nodes.map((n) => ({
    id: n.id,
    label: n.name,
    title: `${n.label} · 出现 ${n.mentions} 次 · 关联 ${n.degree}`,
    value: Math.max(8, Math.min(40, n.degree * 4 + n.mentions)),
    color: {
      background: LABEL_COLORS[n.label] || '#5B8FF9',
      border: '#ffffff',
      highlight: { background: '#409eff', border: '#fff' },
    },
  }))
  const edges = data.edges.map((e) => ({
    id: e.id,
    from: e.source,
    to: e.target,
    label: e.relation,
    title:
      `${e.relation} · 强度 ${e.weight}` +
      (e.source_type === 'manual' ? ' · 手动标注' : ''),
    width: Math.min(6, 1 + e.weight),
    // 手动标注的关系用醒目颜色，区别于自动抽取
    color:
      e.source_type === 'manual'
        ? { color: '#f56c6c', highlight: '#f56c6c' }
        : { color: '#c0c4cc', highlight: '#409eff' },
    dashes: e.source_type === 'manual',
    font: { size: 10, color: '#909399', strokeWidth: 0 },
    smooth: { enabled: true, type: 'continuous' },
  }))

  if (!network) {
    nodesDs = new DataSet(nodes)
    edgesDs = new DataSet(edges)
    network = new Network(
      containerRef.value,
      { nodes: nodesDs, edges: edgesDs },
      {
        nodes: { shape: 'dot', font: { size: 13, color: '#303133' }, borderWidth: 2 },
        edges: { arrows: { to: { enabled: false } } },
        physics: {
          barnesHut: { gravitationalConstant: -8000, springLength: 120, avoidOverlap: 0.3 },
          stabilization: { iterations: 200 },
        },
        interaction: { hover: true, tooltipDelay: 120, navigationButtons: true, keyboard: false },
      },
    )
    network.on('click', (params: any) => {
      if (params.nodes.length) {
        handleNodeClick(params.nodes[0] as number)
      } else if (params.edges.length) {
        handleEdgeClick(params.edges[0] as number)
      }
    })
  } else {
    nodesDs?.clear()
    edgesDs?.clear()
    nodesDs?.add(nodes)
    edgesDs?.add(edges)
  }
  network?.fit({ animation: true })
}

// 点击节点：关联模式下累计选择两个实体
function handleNodeClick(id: number) {
  if (!linkMode.value) {
    const node = graphData.value?.nodes.find((n) => n.id === id)
    if (node) search.value = node.name
    return
  }
  const node = graphData.value?.nodes.find((n) => n.id === id)
  if (!node) return
  if (!linkSource.value) {
    linkSource.value = node
    ElMessage.info(`已选择起点：「${node.name}」，请再点击另一个实体作为终点`)
    network?.selectNodes([id])
  } else if (linkSource.value.id === node.id) {
    ElMessage.warning('不能关联到自身')
  } else {
    linkTarget.value = node
    relDialogVisible.value = true
    network?.selectNodes([linkSource.value.id, node.id])
  }
}

const linkTarget = ref<GraphNode | null>(null)

// 点击边：删除关系
async function handleEdgeClick(id: number) {
  const edge = graphData.value?.edges.find((e) => e.id === id)
  if (!edge) return
  const srcName = graphData.value?.nodes.find((n) => n.id === edge.source)?.name || '?'
  const tgtName = graphData.value?.nodes.find((n) => n.id === edge.target)?.name || '?'
  try {
    await ElMessageBox.confirm(
      `删除关系：「${srcName}」 -[${edge.relation}]-> 「${tgtName}」？`,
      '删除关系',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    const res = await deleteRelation(id)
    ElMessage.success(res.message)
    await loadGraph()
  } catch {
    // 拦截器已提示
  }
}

// 切换关联模式
function toggleLinkMode() {
  linkMode.value = !linkMode.value
  linkSource.value = null
  linkTarget.value = null
  network?.unselectAll()
  if (linkMode.value) {
    ElMessage.info('关联模式：依次点击两个实体即可手动建立关系')
  }
}

// 确认创建手动关系
async function confirmLink() {
  if (!linkSource.value || !linkTarget.value || !pickedRelation.value) return
  linking.value = true
  try {
    await createRelation({
      source_id: linkSource.value.id,
      target_id: linkTarget.value.id,
      relation: pickedRelation.value,
    })
    ElMessage.success(
      `已关联：「${linkSource.value.name}」 -[${pickedRelation.value}]-> 「${linkTarget.value.name}」`,
    )
    relDialogVisible.value = false
    pickedRelation.value = ''
    linkSource.value = null
    linkTarget.value = null
    network?.unselectAll()
    if (linkMode.value) linkMode.value = false
    await loadGraph()
  } catch {
    // 拦截器已提示
  } finally {
    linking.value = false
  }
}

async function rebuild() {
  building.value = true
  try {
    const res = await buildGraph(category.value === '全部' ? undefined : category.value)
    ElMessage.success(res.message + '（你的手动标注已保留）')
    await loadGraph()
  } catch {
    // 拦截器已提示
  } finally {
    building.value = false
  }
}

async function onClear() {
  try {
    await ElMessageBox.confirm(
      '确定清空当前图谱？自动抽取的关系与你的手动标注都将被删除。',
      '清空确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    const res = await clearGraph()
    ElMessage.success(res.message)
    await loadGraph()
  } catch {
    // 拦截器已提示
  }
}

// 搜索高亮：聚焦匹配的节点及其邻居
function focusNode(name: string) {
  if (!network || !graphData.value) return
  const target = graphData.value.nodes.find((n) => n.name === name)
  if (!target) {
    ElMessage.info(`未找到实体「${name}」`)
    return
  }
  const neighborIds = new Set<number>([target.id])
  for (const e of graphData.value.edges) {
    if (e.source === target.id) neighborIds.add(e.target)
    if (e.target === target.id) neighborIds.add(e.source)
  }
  network.selectNodes([target.id])
  network.focus(target.id, { scale: 1.1, animation: true })
  ElMessage.success(`「${name}」关联 ${neighborIds.size - 1} 个实体`)
}

const filteredNodes = computed<GraphNode[]>(() => {
  if (!graphData.value) return []
  if (!search.value.trim()) return graphData.value.nodes
  return graphData.value.nodes.filter((n) => n.name.includes(search.value.trim()))
})

onMounted(async () => {
  try {
    relationTypes.value = await getRelationTypes()
  } catch {
    relationTypes.value = ['属于', '包含', '相关', '对比', '因果', '举例', '用于', '其他']
  }
  await loadGraph()
})
onBeforeUnmount(() => {
  network?.destroy()
  network = null
})
</script>

<template>
  <div class="graph-page">
    <div class="graph-header">
      <div>
        <h2>知识图谱</h2>
        <p class="subtitle">
          从你上传的资料中自动抽取实体与关系，构建可交互的知识网络。
          <template v-if="graphData">
            当前 {{ graphData.entity_count }} 个实体、{{ graphData.relation_count }} 条关系。
          </template>
        </p>
      </div>
      <div class="actions">
        <el-button :loading="building" type="primary" @click="rebuild">重新构建</el-button>
        <el-button :disabled="!graphData || graphData.nodes.length === 0" @click="onClear">
          清空
        </el-button>
      </div>
    </div>

    <div class="graph-toolbar">
      <el-select v-model="category" style="width: 120px" @change="loadGraph">
        <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
      </el-select>

      <el-input
        v-model="search"
        placeholder="搜索实体（如：卷积神经网络）"
        clearable
        style="max-width: 280px"
        @keyup.enter="focusNode(search)"
      >
        <template #append>
          <el-button @click="focusNode(search)">定位</el-button>
        </template>
      </el-input>

      <div class="filter">
        <span>最小关系强度：</span>
        <el-select v-model="minWeight" style="width: 90px" @change="loadGraph">
          <el-option :value="1" label="≥1" />
          <el-option :value="2" label="≥2" />
          <el-option :value="3" label="≥3" />
        </el-select>
      </div>

      <el-button
        :type="linkMode ? 'warning' : 'default'"
        :plain="!linkMode"
        @click="toggleLinkMode"
      >
        {{ linkMode ? '取消关联' : '手动关联' }}
      </el-button>
      <span v-if="linkMode && linkSource" class="link-hint">
        起点：<b>{{ linkSource.name }}</b> → 点击终点实体
      </span>

      <div class="legend">
        <span v-for="(c, k) in LABEL_COLORS" :key="k" class="legend-item">
          <i class="dot" :style="{ background: c }" />{{ k }}
        </span>
        <span class="legend-item">
          <i class="line-manual" />手动标注
        </span>
      </div>
    </div>

    <!-- 选择关系类型对话框 -->
    <el-dialog v-model="relDialogVisible" title="建立关系" width="420px">
      <p v-if="linkSource && linkTarget" class="rel-confirm">
        <b>{{ linkSource.name }}</b>
        <span class="arrow"> ──关系──► </span>
        <b>{{ linkTarget.name }}</b>
      </p>
      <el-form label-width="80px">
        <el-form-item label="关系类型">
          <el-select v-model="pickedRelation" placeholder="选择关系类型" style="width: 100%">
            <el-option v-for="t in relationTypes" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="relDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!pickedRelation" :loading="linking" @click="confirmLink">
          确认关联
        </el-button>
      </template>
    </el-dialog>

    <div class="graph-body">
      <div v-loading="loading" ref="containerRef" class="graph-canvas" />

      <div v-if="isEmpty" class="empty-hint">
        <el-empty description="暂无图谱数据">
          <el-button type="primary" :loading="building" @click="rebuild">从我的资料构建</el-button>
        </el-empty>
      </div>

      <aside class="side-panel">
        <div class="side-title">实体列表（{{ filteredNodes.length }}）</div>
        <el-scrollbar height="100%">
          <div
            v-for="n in filteredNodes"
            :key="n.id"
            class="entity-item"
            @click="focusNode(n.name)"
          >
            <i class="dot" :style="{ background: LABEL_COLORS[n.label] || '#5B8FF9' }" />
            <span class="ename">{{ n.name }}</span>
            <span class="emeta">{{ n.label }} · {{ n.degree }}关联</span>
          </div>
          <el-empty v-if="filteredNodes.length === 0" :image-size="60" description="无匹配实体" />
        </el-scrollbar>
      </aside>
    </div>
  </div>
</template>

<style scoped lang="scss">
.graph-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 140px);
}
.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 12px;
  h2 { margin: 0; }
  .subtitle { color: #888; margin: 4px 0 0; font-size: 13px; }
}
.graph-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  .filter { display: flex; align-items: center; gap: 6px; color: #606266; font-size: 13px; }
  .legend { display: flex; gap: 12px; margin-left: auto; flex-wrap: wrap; }
  .legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #606266; }
  .line-manual { display: inline-block; width: 18px; height: 0; border-top: 2px dashed #f56c6c; }
  .link-hint { font-size: 12px; color: #e6a23c; }
}
.rel-confirm {
  text-align: center; font-size: 15px; color: #303133; margin: 0 0 16px;
  .arrow { color: #909399; margin: 0 6px; }
}
.dot {
  display: inline-block; width: 10px; height: 10px; border-radius: 50%;
}
.graph-body {
  flex: 1;
  display: flex;
  gap: 12px;
  min-height: 0;
  position: relative;
}
.graph-canvas {
  flex: 1;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fafbfc;
  overflow: hidden;
}
.empty-hint {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;
  :deep(.el-empty) { pointer-events: auto; }
}
.side-panel {
  width: 260px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  padding: 12px;
}
.side-title { font-weight: 600; margin-bottom: 8px; color: #303133; }
.entity-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; border-radius: 8px; cursor: pointer;
  &:hover { background: #f4f6f8; }
  .ename { font-size: 13px; color: #303133; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .emeta { font-size: 11px; color: #b0b3b8; flex-shrink: 0; }
}
</style>
