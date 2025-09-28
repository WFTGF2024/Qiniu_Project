<template>
  <div class="chat-wrap">
    <ChatHeader :role="role">
      <div class="row">
        <TTSVoicePicker v-model="tts" />
        <button class="btn ghost" @click="toggleVoice">{{ settings.voiceEnabled ? '🔊 TTS开' : '🔇 TTS关' }}</button>
        <button class="btn ghost" @click="exportChat">导出</button>
        <button class="btn" :disabled="!canSave" @click="save">保存</button>
      </div>
    </ChatHeader>
    <LoginGate v-if="!isLogin" />

    <div class="chat-list">
      <MessageBubble
        v-for="(m,i) in messages"
        :key="i"
        :who="m.role==='user'?'user':'ai'"
        :text="m.content"
        :avatar="m.role==='user'?'👤':role.avatar || '🤖'"
      >
        <template #meta>
          <span>{{ new Date(m.ts).toLocaleTimeString() }}</span>
          <a v-if="m.audioUrl" :href="m.audioUrl" target="_blank">播放音频</a>
        </template>
      </MessageBubble>
    </div>

    <DeepQuestionChips :items="deepQuestions" @pick="useQuestion" />

    <div class="chat-input">
      <input class="input" v-model="text" placeholder="说点什么…" style="flex:1;" @keydown.enter="sendText" />
      <AudioRecorder @done="onAudioDone" />
      <button class="btn" :disabled="pending" @click="sendText">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useChatStore } from '../store/chat'
import { useUserStore } from '../store/user'
import { buildSystemPrompt } from '../utils/prompts'
import { chatStream, chatOnce } from '../api/llm'
import { asrFull } from '../api/asr'
import { synthesizeTTS } from '../api/tts'
import { saveChat } from '../api/core'
import AudioRecorder from '../components/AudioRecorder.vue'
import MessageBubble from '../components/MessageBubble.vue'
import DeepQuestionChips from '../components/DeepQuestionChips.vue'
import LoginGate from '../components/LoginGate.vue'
import TTSVoicePicker from '../components/TTSVoicePicker.vue'
import ChatHeader from '../components/ChatHeader.vue'

const chat = useChatStore()
const user = useUserStore()
const text = ref('')
const tts = ref({ style: chat.settings.ttsStyle, emoWeight: chat.settings.emoWeight })
const role = computed(()=> chat.currentRole)
const messages = computed(()=> chat.messages)
const deepQuestions = computed(()=> chat.deepQuestions)
const settings = chat.settings
const isLogin = computed(()=> user.isLogin)
const pending = computed(()=> chat.pending)
const canSave = computed(()=> user.isLogin && chat.messages.length>0)

watch(tts, (v)=>{
  chat.settings.ttsStyle = v.style
  chat.settings.emoWeight = v.emoWeight
}, { deep:true })

function parseDeepQuestions(text){
  const m = text.match(/\[DEEP_QUESTIONS\]([\s\S]*?)\[END\]/i)
  if(!m) return []
  const lines = m[1].split(/\n|\r/).map(s=>s.trim()).filter(Boolean)
  return lines.map(s=> s.replace(/^[-•\d\.\)\s]*/,'').trim()).filter(Boolean).slice(0,2)
}

async function onAudioDone(wav){
  // 1) ASR
  const transcript = await asrFull(wav)
  chat.addMessage({ role:'user', content: transcript, audioUrl: URL.createObjectURL(wav) })
  // 2) LLM 回复
  await converse(transcript)
}

function useQuestion(q){
  text.value = q
}

async function sendText(){
  if(!text.value.trim()) return
  const userText = text.value.trim()
  chat.addMessage({ role:'user', content: userText })
  text.value = ''
  await converse(userText)
}

async function converse(userText) {
  chat.pending = true
  try {
    const system = buildSystemPrompt({
      role: role.value,
      memorySummary: chat.memorySummary,
      userPrefs: {}
    })
    const sysWithKB = chat.kbContext 
      ? system + `\n\n【外部上下文，供参考】\n` + chat.kbContext 
      : system

    let msgs = []

    if (user.isLogin) {
      // 登录用户：带历史消息
      msgs = [{ role: 'system', content: sysWithKB }]
      for (const m of chat.messages) {
        if (m.role === 'user' || m.role === 'assistant') {
          msgs.push({ role: m.role, content: m.content })
        }
      }
      msgs.push({ role: 'user', content: userText })
    } else {
      // 🚫 免登录用户：只带 system + 当前问题
      msgs = [
        { role: 'system', content: sysWithKB },
        { role: 'user', content: userText }
      ]
    }

    let full = ''
    if (settings.stream) {
      await chatStream({
        messages: msgs,
        onDelta: (delta, acc) => {
          if (!full) {
            chat.addMessage({ role: 'assistant', content: delta })
            full = delta
          } else {
            full += delta
            chat.messages[chat.messages.length - 1].content = full
          }
        },
        onDone: () => {}
      })
    } else {
      const content = await chatOnce(msgs)
      chat.addMessage({ role: 'assistant', content })
      full = content
    }

    // deep questions
    const qs = parseDeepQuestions(full)
    chat.setDeepQuestions(qs)

  } catch (e) {
    chat.addMessage({ role: 'assistant', content: '【系统】对话失败：' + e.message })
  } finally {
    chat.pending = false
  }
}


async function exportChat(){
  const payload = { role: role.value, messages: chat.messages, ts: Date.now() }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type:'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `chat-${role.value.id}-${Date.now()}.json`
  a.click()
}

async function save(){
  if(!user.isLogin) return
  const payload = { role: role.value, messages: chat.messages, ts: Date.now() }
  const b64 = btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
  const dataUrl = 'data:application/json;base64,' + b64
  const record_id = role.value.id + '-' + Date.now()
  const res = await saveChat({ user_id: user.user?.user_id, record_id, content_url: dataUrl })
  alert('已保存：' + JSON.stringify(res))
}

function toggleVoice(){ chat.settings.voiceEnabled = !chat.settings.voiceEnabled }
</script>