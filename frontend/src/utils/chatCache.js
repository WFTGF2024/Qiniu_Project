// 简单 localStorage 多会话缓存
const LIST_KEY = 'chat:list:v1'
const SESSION_KEY = (id) => `chat:session:${id}`

const readJSON = (k, d=null) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d } catch { return d } }
const writeJSON = (k, v) => localStorage.setItem(k, JSON.stringify(v))

export function listChats() {
  return readJSON(LIST_KEY, [])
}

export function createChat(title='新会话') {
  const id = String(Date.now()) + Math.random().toString(16).slice(2,8)
  const list = listChats()
  const item = { id, title, updatedAt: Date.now() }
  writeJSON(LIST_KEY, [item, ...list])
  writeJSON(SESSION_KEY(id), { ts: Date.now(), messages: [] })
  return item
}

export function renameChat(id, title) {
  const list = listChats().map(x => x.id===id ? { ...x, title, updatedAt: Date.now() } : x)
  writeJSON(LIST_KEY, list)
}

export function deleteChat(id) {
  const list = listChats().filter(x => x.id !== id)
  writeJSON(LIST_KEY, list)
  localStorage.removeItem(SESSION_KEY(id))
}

export function loadChat(id) {
  const s = readJSON(SESSION_KEY(id))
  return s && Array.isArray(s.messages) ? s.messages : []
}

export function saveChat(id, messages) {
  writeJSON(SESSION_KEY(id), { ts: Date.now(), messages })
  const list = listChats().map(x => x.id===id ? { ...x, updatedAt: Date.now() } : x)
  writeJSON(LIST_KEY, list)
}
