import { httpASR } from './http'

export async function asrFull(wavBlob){
  const fd = new FormData()
  fd.append('file', wavBlob, 'speech.wav')
  const { data } = await httpASR.post('/asr', fd, { headers:{ 'Content-Type':'multipart/form-data' } })
  return data.text || ''
}