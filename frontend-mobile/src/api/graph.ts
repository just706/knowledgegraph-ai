import request from '@/utils/request'

export interface GraphNode {
  id: number
  name: string
  label: string
  /** 出现次数（后端 GraphNode 同时返回 mentions / mention_count，这里对齐移动端命名） */
  mention_count: number
  /** 实体来源分类（从 entity_sources 聚合），可能为空 */
  categories: string[]
  /** 关联度（相邻边数），用于节点大小/排序 */
  degree?: number
}

export interface GraphEdge {
  id: number
  source: number
  target: number
  relation: string
  weight: number
  source_type?: string
}

export function getGraph(category?: string): Promise<{
  nodes: GraphNode[]
  edges: GraphEdge[]
  entity_count?: number
  relation_count?: number
}> {
  return request.get('/graph', { params: { category } })
}

export function getRelationTypes(): Promise<string[]> {
  return request.get('/graph/relation-types')
}

/** 基于用户全部资料重新构建图谱。category 可选，仅构建该分类。 */
export function buildGraph(category?: string): Promise<{
  entity_count: number
  relation_count: number
  message: string
}> {
  return request.post('/graph/build', null, { params: { category } })
}

/** 清空当前用户的图谱。 */
export function clearGraph(): Promise<{ deleted_entities: number; message: string }> {
  return request.delete('/graph/clear')
}
