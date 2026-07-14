import request from '@/utils/request'

export interface GraphNode {
  id: number
  name: string
  label: string
  mentions: number
  degree: number
}

export interface GraphEdge {
  id: number
  source: number
  target: number
  relation: string
  weight: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  entity_count: number
  relation_count: number
}

export interface GraphBuildResult {
  entity_count: number
  relation_count: number
  message: string
}

/** 获取当前用户的图谱数据（节点 + 边）。 */
export function getGraph(minWeight = 1): Promise<GraphData> {
  return request.get('/graph', { params: { min_weight: minWeight } })
}

/** 基于用户全部资料重新构建图谱。 */
export function buildGraph(): Promise<GraphBuildResult> {
  return request.post('/graph/build')
}

/** 清空当前用户的图谱。 */
export function clearGraph(): Promise<{ deleted_entities: number; message: string }> {
  return request.delete('/graph/clear')
}

/** 获取可标注的关系类型列表。 */
export function getRelationTypes(): Promise<string[]> {
  return request.get('/graph/relation-types')
}

/** 用户手动创建一条关系（实体 A -关系-> 实体 B）。 */
export function createRelation(payload: {
  source_id: number
  target_id: number
  relation: string
}): Promise<GraphEdge> {
  return request.post('/graph/relations', payload)
}

/** 删除一条关系。 */
export function deleteRelation(relationId: number): Promise<{ deleted: number; message: string }> {
  return request.delete(`/graph/relations/${relationId}`)
}
