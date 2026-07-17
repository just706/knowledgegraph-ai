import request from '@/utils/request'

export interface GraphNode {
  id: number
  name: string
  label: string
  mention_count: number
  categories: string[]
}

export interface GraphEdge {
  id: number
  source: number
  target: number
  relation: string
  weight: number
}

export function getGraph(category?: string): Promise<{
  nodes: GraphNode[]
  edges: GraphEdge[]
}> {
  return request.get('/graph', { params: { category } })
}

export function getRelationTypes(): Promise<string[]> {
  return request.get('/graph/relation-types')
}
