// src/api/tts.js
export async function synthesizeTTS({ text, style='style1', emoWeight=0.65, temperature=0.8, format='wav' }){
  const fd = new FormData()
  fd.append('text', text)
  fd.append('style', style)
  fd.append('emo_weight', String(emoWeight))
  fd.append('temperature', String(temperature))
  fd.append('format', format)
  // 建议仍走 Vite 代理：/tts/synthesize（若直连请确保后端已返回 CORS 头）
  const resp = await fetch('/tts/synthesize', { method:'POST', body: fd })
  if(!resp.ok) throw new Error('TTS fail: ' + resp.status)
  return await resp.blob()        // 返回 Blob，方便播放或下载二选一
}

// ✅ 新增：一键下载 wav 文件（不会往聊天里塞 audioUrl）
export async function downloadTTSFile({ text, style='style1', emoWeight=0.65, temperature=0.8, filename }){
  const blob = await synthesizeTTS({ text, style, emoWeight, temperature, format:'wav' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || `tts_${Date.now()}.wav`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
