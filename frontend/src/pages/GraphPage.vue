<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataSet } from 'vis-data'
import { Network } from 'vis-network'
import { getGraph, buildGraph, clearGraph, type GraphData, type GraphNode } from '@/api/graph'

const graphData = ref<GraphData | null>(null)
const loading = ref(false)
const building = ref(false)
const search = ref('')
const minWeight = ref(1)

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
    const data = await getGraph(minWeight.value)
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
    title: `${e.relation} · 强度 ${e.weight}`,
    width: Math.min(6, 1 + e.weight),
    font: { size: 10, color: '#909399', strokeWidth: 0 },
    color: { color: '#c0c4cc', highlight: '#409eff' },
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
        const id = params.nodes[0] as number
        const node = graphData.value?.nodes.find((n) => n.id === id)
        if (node) search.value = node.name
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

async function rebuild() {
  building.value = true
  try {
    const res = await buildGraph()
    ElMessage.success(res.message)
    await loadGraph()
  } catch {
    // 拦截器已提示
  } finally {
    building.value = false
  }
}

async function onClear() {
  try {
    await ElMessageBox.confirm('确定清空当前图谱？该操作不可恢复。', '清空确认', {
      type: 'warning',
    })
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

      <div class="legend">
        <span v-for="(c, k) in LABEL_COLORS" :key="k" class="legend-item">
          <i class="dot" :style="{ background: c }" />{{ k }}
        </span>
      </div>
    </div>

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
