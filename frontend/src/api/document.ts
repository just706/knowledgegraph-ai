import request from '@/utils/request'

export interface DocumentItem {
  id: number
  filename: string
  title: string
  file_type: string
  file_size: number
  chunk_count: number
  status: string
  created_at: string
}

export interface DocumentChunk {
  id: number
  document_id: number
  chunk_index: number
  content: string
  token_estimate: number
}

export interface DocumentDetail extends DocumentItem {
  chunks: DocumentChunk[]
}

export function uploadDocument(file: File): Promise<DocumentItem> {
  const form = new FormData()
  form.append('file', file)
  return request.post('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listDocuments(): Promise<DocumentItem[]> {
  return request.get('/documents')
}

export function getDocument(id: number): Promise<DocumentDetail> {
  return request.get(`/documents/${id}`)
}

export function deleteDocument(id: number): Promise<void> {
  return request.delete(`/documents/${id}`)
}
