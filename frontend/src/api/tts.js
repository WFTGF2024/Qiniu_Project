import { httpTTS } from './http'

export async function synthesizeTTS({ text, style='style1', emoWeight=0.65, temperature=0.8 }){
  const fd = new FormData()
  fd.append('text', text)
  fd.append('style', style)
  fd.append('emo_weight', String(emoWeight))
  fd.append('temperature', String(temperature))
  // emo_control_method=0 表示关闭；服务端会使用默认参考音频
  const resp = await fetch(new URL('/synthesize', httpTTS.defaults.baseURL).toString(), {
    method:'POST',
    body: fd
  })
  if(!resp.ok){ throw new Error('TTS fail: ' + resp.status) }
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  return url
}