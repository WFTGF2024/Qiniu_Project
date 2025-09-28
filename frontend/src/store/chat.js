import { defineStore } from 'pinia'
import roles from '../data/roles'

export const useChatStore = defineStore('chat', {
  state: ()=>({
    currentRole: roles[0],
    messages: [],     // {role:'user'|'assistant'|'system', content, ts, audioUrl?}
    memorySummary: '',
    deepQuestions: [],
    pending: false,
    settings: {
      temperature: 0.7,
      ttsStyle: 'style1',
      emoWeight: 0.65,
      voiceEnabled: true,
      stream: true
    },
    kbContext: '' // 由右侧知识面板注入的上下文
  }),
  actions:{
    setCurrentRole(role){
      this.currentRole = role
      this.messages = []
      this.memorySummary = ''
      this.deepQuestions = []
    },
    addMessage(m){
      this.messages.push({ ...m, ts: Date.now() })
    },
    setDeepQuestions(qs){
      this.deepQuestions = qs || []
    },
    setKbContext(text){
      this.kbContext = text || ''
    }
  }
})