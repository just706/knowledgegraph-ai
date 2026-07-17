import request from '@/utils/request'

export interface MindmapNode {
  id: string
  label: string
  children?: MindmapNode[]
}

export function getMindmap(category?: string): Promise<{
  root: MindmapNode
  categories: string[]
}> {
  return request.get('/mindmap', { params: { category } })
}
