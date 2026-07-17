import request from '@/utils/request'

export interface DocumentItem {
  id: number
  filename: string
  title: string
  file_type: string
  file_size: number
  chunk_count: number
  status: string
  category: string
  graph_status: string
  graph_error: string | null
  created_at: string
}

export function uploadDocument(file: File, category?: string): Promise<DocumentItem> {
  const form = new FormData()
  form.append('file', file)
  if (category) form.append('category', category)
  return request.post('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listDocuments(): Promise<DocumentItem[]> {
  return request.get('/documents')
}

export function deleteDocument(id: number): Promise<void> {
  return request.delete(`/documents/${id}`)
}
