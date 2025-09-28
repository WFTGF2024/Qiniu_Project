import { httpLLM } from './http'

export async function chatOnce(messages, model=null){
  const body = { messages }
  if(model) body.model = model
  const { data } = await httpLLM.post('/api/chat', body)
  return data.content
}

// 流式：逐字回调
export async function chatStream({ messages, onDelta, onDone }) {
  const url = new URL('/api/chat/stream', httpLLM.defaults.baseURL).toString()

  // 🚫 不传 model，只传 messages
  const body = { messages }

  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })

  if (!resp.body) throw new Error('No stream body')
  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let text = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    for (const line of chunk.split('\n').filter(Boolean)) {
      try {
        const obj = JSON.parse(line)
        if (obj.delta) {
          text += obj.delta
          onDelta && onDelta(obj.delta, text)
        } else if (obj.event === 'done') {
          onDone && onDone(text)
        }
      } catch (e) {
        // ignore bad line
      }
    }
  }
  return text
}
