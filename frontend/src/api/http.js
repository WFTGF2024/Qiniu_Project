import axios from 'axios'

const LLM_BASE = import.meta.env.VITE_LLM_BASE || 'http://127.0.0.1:7207'
const ASR_BASE = import.meta.env.VITE_ASR_BASE || 'http://127.0.0.1:7205'
const TTS_BASE = import.meta.env.VITE_TTS_BASE || 'http://127.0.0.1:7206'
const CORE_BASE = import.meta.env.VITE_CORE_BASE || 'http://127.0.0.1:7210'

export const httpCore = axios.create({ baseURL: CORE_BASE, timeout: 20000 })
export const httpLLM  = axios.create({ baseURL: LLM_BASE,  timeout: 60000 })
export const httpASR  = axios.create({ baseURL: ASR_BASE,  timeout: 60000 })
export const httpTTS  = axios.create({ baseURL: TTS_BASE,  timeout: 60000 })

function getToken(){ return localStorage.getItem('token') || '' }
[httpCore, httpLLM, httpASR, httpTTS].forEach((inst)=>{
  inst.interceptors.request.use((cfg)=>{
    const t = getToken()
    if(t) cfg.headers.Authorization = `Bearer ${t}`
    return cfg
  })
})

export const endpoints = { LLM_BASE, ASR_BASE, TTS_BASE, CORE_BASE }