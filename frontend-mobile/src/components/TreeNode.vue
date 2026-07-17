<template>
  <div :style="{ marginLeft: `${depth * 16}px`, padding: '4px 0' }">
    <div
      :style="{ display: 'flex', alignItems: 'center', cursor: hasChildren ? 'pointer' : 'default' }"
      @click="toggle"
    >
      <span v-if="hasChildren" style="margin-right: 4px; color: #969799">{{ collapsed ? '▶' : '▼' }}</span>
      <span>{{ node.label }}</span>
    </div>
    <div v-if="!collapsed && hasChildren">
      <TreeNode
        v-for="(child, i) in node.children"
        :key="i"
        :node="child"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { MindmapNode } from '@/api/mindmap'

const props = defineProps<{
  node: MindmapNode
  depth: number
}>()

const collapsed = ref(false)
const hasChildren = computed(() => (props.node.children?.length || 0) > 0)

function toggle() {
  if (hasChildren.value) collapsed.value = !collapsed.value
}
</script>
