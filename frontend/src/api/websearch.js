import { httpCore } from './http'

export async function ingestUrl(url){
  const { data } = await httpCore.post('/web/ingest', { url })
  return data
}

export async function webSearch({ q, top_k=5, mode='hybrid', alpha=0.6 }){
  const { data } = await httpCore.post('/web/search', { q, top_k, mode, alpha })
  return data
}

export async function getPage(page_id){
  const { data } = await httpCore.get('/web/page', { params:{ page_id } })
  return data
}