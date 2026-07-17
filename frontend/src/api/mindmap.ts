import request from '@/utils/request'

export interface MindNode {
  name: string
  kind: string
  entity_id: number | null
  meta: Record<string, any>
  children: MindNode[]
}

export interface MindmapData {
  mode: string
  root: MindNode
  node_count: number
}

/** 获取当前用户的思维导图（由知识图谱投影生成）。category 可选，按分类生成。 */
export function getMindmap(category?: string): Promise<MindmapData> {
  return request.get('/mindmap', { params: { category } })
}
