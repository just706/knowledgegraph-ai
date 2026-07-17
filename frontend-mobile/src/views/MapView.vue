<template>
  <div class="map-view">
    <van-nav-bar :title="activeTab === 'graph' ? '知识图谱' : '思维导图'" />

    <van-tabs v-model:active="activeTab" sticky>
      <van-tab title="知识图谱" name="graph" />
      <van-tab title="思维导图" name="mindmap" />
    </van-tabs>

    <!-- 图谱 -->
    <div v-show="activeTab === 'graph'" class="graph-area" ref="graphEl" @touchstart="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd">
      <van-empty v-if="loading" description="加载中..." />
      <div v-else-if="nodes.length === 0" class="graph-empty">
        <van-empty description="暂无图谱数据">
          <template #bottom>
            <van-button type="primary" size="small" :loading="building" @click="rebuild">
              从我的资料构建
            </van-button>
          </template>
        </van-empty>
      </div>
      <svg
        v-else
        class="graph-svg"
        :width="svgW"
        :height="svgH"
      >
        <g :transform="`translate(${pan.x},${pan.y}) scale(${scale})`">
          <line
            v-for="(e, i) in edges"
            :key="'e' + i"
            :x1="pos[e.source]?.x"
            :y1="pos[e.source]?.y"
            :x2="pos[e.target]?.x"
            :y2="pos[e.target]?.y"
            :stroke="isEdgeActive(e) ? '#1989fa' : '#ebedf0'"
            :stroke-width="isEdgeActive(e) ? 2 : 1"
          />
          <g
            v-for="n in nodes"
            :key="n.id"
            :transform="`translate(${pos[n.id]?.x},${pos[n.id]?.y})`"
            class="node"
            @click.stop="onNodeClick(n)"
          >
            <circle
              :r="nodeRadius(n)"
              :fill="selected === n.id ? '#1989fa' : nodeColor(n)"
              :stroke="selected === n.id ? '#1989fa' : '#ffffff'"
              stroke-width="2"
            />
            <text
              :y="nodeRadius(n) + 12"
              text-anchor="middle"
              font-size="11"
              :fill="selected === n.id ? '#1989fa' : '#323233'"
            >{{ n.name }}</text>
          </g>
        </g>
      </svg>

      <div v-if="activeTab === 'graph' && nodes.length" class="graph-tools">
        <van-icon name="plus" @click="zoomBy(0.2)" />
        <van-icon name="minus" @click="zoomBy(-0.2)" />
        <van-icon name="replay" @click="resetView" />
      </div>

      <van-popup v-model:show="showNode" position="bottom" round :style="{ height: 'auto' }">
        <div class="node-panel" v-if="activeNode">
          <div class="np-head">
            <i class="np-dot" :style="{ background: nodeColor(activeNode) }" />
            <h3>{{ activeNode.name }}</h3>
          </div>
          <p class="label">类型：{{ activeNode.label || '其他' }}</p>
          <p class="meta">
            提及 {{ activeNode.mention_count || 0 }} 次 · 关联 {{ relatedEdges.length }} 条
          </p>
          <p class="meta" v-if="(activeNode.categories || []).length">
            分类：{{ activeNode.categories.join(' / ') }}
          </p>
          <p class="rel" v-if="relatedEdges.length">
            关系：{{ relatedEdges.map((e) => e.relation).join('、') }}
          </p>
          <div class="np-actions">
            <van-button size="small" type="primary" plain @click="rebuild">重建图谱</van-button>
            <van-button size="small" type="danger" plain @click="onClear">清空</van-button>
          </div>
        </div>
      </van-popup>

      <div v-if="activeTab === 'graph' && nodes.length" class="graph-legend">
        <span v-for="(c, k) in LABEL_COLORS" :key="k" class="lg-item">
          <i class="lg-dot" :style="{ background: c }" />{{ k }}
        </span>
      </div>
    </div>

    <!-- 思维导图 -->
    <div v-show="activeTab === 'mindmap'" class="mindmap-area">
      <van-empty v-if="!mindmap" description="暂无导图数据" />
      <div v-else class="tree">
        <TreeNode :node="mindmap.root" :depth="0" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import { getGraph, buildGraph, clearGraph, type GraphNode, type GraphEdge } from '@/api/graph'
import { getMindmap, type MindmapNode } from '@/api/mindmap'
import TreeNode from '@/components/TreeNode.vue'

const activeTab = ref('graph')
const graphEl = ref<HTMLElement | null>(null)
const svgW = ref(300)
const svgH = ref(400)
const loading = ref(false)
const building = ref(false)

const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const mindmap = ref<{ root: MindmapNode } | null>(null)

// 按标签着色（与 PC 端 GraphPage 配色保持一致）
const LABEL_COLORS: Record<string, string> = {
  概念: '#5B8FF9',
  方法: '#61DDAA',
  结构: '#F6BD16',
  术语: '#7262FD',
  人物: '#ff9845',
  其他: '#bfbfbf',
}
function nodeColor(n: GraphNode): string {
  return LABEL_COLORS[n.label] || '#5B8FF9'
}

type P = { x: number; y: number; vx: number; vy: number }
const pos = ref<Record<number, P>>({})

// 视图变换
const scale = ref(1)
const pan = ref({ x: 0, y: 0 })
const selected = ref<number | null>(null)
const showNode = ref(false)
const activeNode = ref<GraphNode | null>(null)

let simTimer: number | null = null

function nodeRadius(n: GraphNode): number {
  const mc = n.mention_count || 0
  return Math.min(18, 8 + Math.log(mc + 1) * 3)
}

const relatedEdges = ref<GraphEdge[]>([])
function refreshRelated() {
  if (selected.value == null) {
    relatedEdges.value = []
    return
  }
  relatedEdges.value = edges.value.filter((e) => e.source === selected.value || e.target === selected.value)
}

function isEdgeActive(e: GraphEdge): boolean {
  return selected.value != null && (e.source === selected.value || e.target === selected.value)
}

async function loadGraph() {
  loading.value = true
  try {
    const res = await getGraph()
    nodes.value = res.nodes || []
    edges.value = res.edges || []
    if (nodes.value.length > 0) {
      await nextTick()
      measure()
      initPositions()
      startSimulation()
    }
  } finally {
    loading.value = false
  }
}

// 从用户资料构建/重建图谱
async function rebuild() {
  if (building.value) return
  building.value = true
  try {
    const res = await buildGraph()
    showToast(res.message + '（手动标注已保留）')
    selected.value = null
    await loadGraph()
  } catch {
    // 拦截器已提示
  } finally {
    building.value = false
  }
}

// 清空图谱
async function onClear() {
  try {
    await showConfirmDialog({
      title: '清空图谱',
      message: '确定清空当前图谱？自动抽取的关系与你的手动标注都将被删除。',
    })
  } catch {
    return
  }
  try {
    const res = await clearGraph()
    showToast(res.message)
    await loadGraph()
  } catch {
    // 拦截器已提示
  }
}

function measure() {
  if (!graphEl.value) return
  svgW.value = graphEl.value.clientWidth
  svgH.value = graphEl.value.clientHeight
}

function initPositions() {
  const w = svgW.value
  const h = svgH.value
  const p: Record<number, P> = {}
  nodes.value.forEach((n, i) => {
    const angle = (i / Math.max(1, nodes.value.length)) * Math.PI * 2
    const r = Math.min(w, h) * 0.35
    p[n.id] = {
      x: w / 2 + Math.cos(angle) * r,
      y: h / 2 + Math.sin(angle) * r,
      vx: 0,
      vy: 0,
    }
  })
  pos.value = p
}

function startSimulation() {
  if (simTimer) cancelAnimationFrame(simTimer)
  const w = svgW.value
  const h = svgH.value
  let steps = 0
  const tick = () => {
    const p = pos.value
    const k = 0.02 // 向心
    const rep = 1200 // 斥力
    const spr = 0.01 // 弹簧
    const rest = 90

    nodes.value.forEach((a) => {
      let dx = 0, dy = 0
      nodes.value.forEach((b) => {
        if (a.id === b.id) return
        const pa = p[a.id], pb = p[b.id]
        let ddx = pa.x - pb.x, ddy = pa.y - pb.y
        let dist = Math.sqrt(ddx * ddx + ddy * ddy) || 1
        const f = rep / (dist * dist)
        dx += (ddx / dist) * f
        dy += (ddy / dist) * f
      })
      // 向心力
      dx += (w / 2 - p[a.id].x) * k
      dy += (h / 2 - p[a.id].y) * k
      p[a.id].vx = (p[a.id].vx + dx) * 0.85
      p[a.id].vy = (p[a.id].vy + dy) * 0.85
    })

    // 弹簧（边）
    edges.value.forEach((e) => {
      const pa = p[e.source], pb = p[e.target]
      if (!pa || !pb) return
      let ddx = pb.x - pa.x, ddy = pb.y - pa.y
      let dist = Math.sqrt(ddx * ddx + ddy * ddy) || 1
      const f = (dist - rest) * spr
      const fx = (ddx / dist) * f, fy = (ddy / dist) * f
      pa.vx += fx; pa.vy += fy
      pb.vx -= fx; pb.vy -= fy
    })

    nodes.value.forEach((n) => {
      const pt = p[n.id]
      pt.x += pt.vx
      pt.y += pt.vy
    })
    pos.value = { ...p }
    steps++
    if (steps < 200) simTimer = requestAnimationFrame(tick)
  }
  simTimer = requestAnimationFrame(tick)
}

function onNodeClick(n: GraphNode) {
  selected.value = selected.value === n.id ? null : n.id
  activeNode.value = n
  refreshRelated()
  showNode.value = true
}

function zoomBy(delta: number) {
  scale.value = Math.min(3, Math.max(0.4, scale.value + delta))
}

function resetView() {
  scale.value = 1
  pan.value = { x: 0, y: 0 }
  selected.value = null
}

// 手势：单指拖拽平移，双指缩放
let gesture: {
  mode: 'none' | 'pan' | 'zoom'
  startX: number
  startY: number
  startPan: { x: number; y: number }
  startDist: number
  startScale: number
} = { mode: 'none', startX: 0, startY: 0, startPan: { x: 0, y: 0 }, startDist: 0, startScale: 1 }

function dist(t0: Touch, t1: Touch): number {
  return Math.hypot(t0.clientX - t1.clientX, t0.clientY - t1.clientY)
}

function onTouchStart(e: TouchEvent) {
  if (e.touches.length === 1) {
    gesture = {
      mode: 'pan',
      startX: e.touches[0].clientX,
      startY: e.touches[0].clientY,
      startPan: { ...pan.value },
      startDist: 0,
      startScale: scale.value,
    }
  } else if (e.touches.length === 2) {
    gesture = {
      mode: 'zoom',
      startX: 0, startY: 0,
      startPan: { ...pan.value },
      startDist: dist(e.touches[0], e.touches[1]),
      startScale: scale.value,
    }
  }
}

function onTouchMove(e: TouchEvent) {
  if (gesture.mode === 'pan' && e.touches.length === 1) {
    const dx = e.touches[0].clientX - gesture.startX
    const dy = e.touches[0].clientY - gesture.startY
    pan.value = { x: gesture.startPan.x + dx, y: gesture.startPan.y + dy }
  } else if (gesture.mode === 'zoom' && e.touches.length === 2) {
    const d = dist(e.touches[0], e.touches[1])
    if (gesture.startDist > 0) {
      const ns = Math.min(3, Math.max(0.4, gesture.startScale * (d / gesture.startDist)))
      scale.value = ns
    }
  }
  e.preventDefault()
}

function onTouchEnd(e: TouchEvent) {
  if (e.touches.length === 0) gesture.mode = 'none'
}

async function loadMindmap() {
  try {
    const res = await getMindmap()
    mindmap.value = { root: res.root }
  } catch {
    mindmap.value = null
  }
}

watch(activeTab, (tab) => {
  if (tab === 'graph') loadGraph()
  else loadMindmap()
})

onMounted(() => {
  loadGraph()
  window.addEventListener('resize', measure)
})

onBeforeUnmount(() => {
  if (simTimer) cancelAnimationFrame(simTimer)
  window.removeEventListener('resize', measure)
})
</script>

<style scoped lang="scss">
.map-view {
  min-height: calc(100vh - 50px);
}

.graph-area {
  height: calc(100vh - 50px - 90px);
  overflow: hidden;
  background: var(--kg-card);
  position: relative;
  touch-action: none;
}

.graph-svg {
  display: block;
}

.node {
  cursor: pointer;
}

.graph-tools {
  position: absolute;
  right: 12px;
  bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;

  .van-icon {
    width: 38px;
    height: 38px;
    background: #fff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    color: var(--kg-primary);
  }
}

.graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-legend {
  position: absolute;
  left: 12px;
  top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  max-width: 70%;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 8px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08);

  .lg-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--kg-text-secondary);
  }
  .lg-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
  }
}

.node-panel {
  padding: 20px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom));

  h3 { margin: 0; font-size: 18px; }
  .np-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .np-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .label { color: var(--kg-text-secondary); margin: 4px 0; }
  .meta { font-size: 13px; color: var(--kg-text-secondary); margin: 4px 0; }
  .rel { font-size: 13px; color: var(--kg-primary); margin: 4px 0; }
  .np-actions {
    display: flex;
    gap: 12px;
    margin-top: 16px;
    :deep(.van-button) { flex: 1; }
  }
}

.mindmap-area {
  padding: 16px;
  background: var(--kg-bg);
}

.tree {
  font-size: 14px;
}
</style>
