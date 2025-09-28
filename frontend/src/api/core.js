import { httpCore } from './http'

export async function register(payload){
  const { data } = await httpCore.post('/api/auth/register', payload)
  return data
}

export async function login({ username, password }){
  const { data } = await httpCore.post('/api/auth/login', { username, password })
  return data
}

export async function me(){
  const { data } = await httpCore.get('/api/auth/me')
  return data
}

// 聊天记录（简化：将 JSON 压缩为 base64 data URL 存到 content_url 字段）
export async function saveChat({ user_id, record_id, content_url }){
  const { data } = await httpCore.post('/chat/api/chat/save', { user_id, record_id, content_url })
  return data
}
export async function listChats(user_id){
  const { data } = await httpCore.get(`/chat/api/chat/${user_id}`)
  return data
}

// 会员
export async function getMembership(user_id){
  const { data } = await httpCore.get(`/api/membership/${user_id}`)
  return data
}
export async function listOrders(user_id){
  const { data } = await httpCore.get(`/api/membership/orders/${user_id}`)
  return data
}
export async function createOrder({ user_id, duration_months, amount, payment_method }){
  const { data } = await httpCore.post('/api/membership/orders', { user_id, duration_months, amount, payment_method })
  return data
}