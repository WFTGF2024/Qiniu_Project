<template>
  <div class="chat-wrap">
    <ChatHeader :role="role">
      <div class="row">
        <!-- 多会话：选择 / 新建 / 删除（若未接入 chatCache，可把这三项去掉） -->
        <select v-model="chatId" class="select" style="margin-right:8px" v-if="chatList.length">
          <option v-for="c in chatList" :key="c.id" :value="c.id">{{ c.title }}</option>
        </select>
        <button class="btn ghost" @click="newChat" title="新建会话">＋新建</button>
        <button class="btn ghost danger" :disabled="!chatId" @click="removeChat" title="删除当前会话">🗑 删除</button>

        <TTSVoicePicker v-model="tts" />
        <button class="btn ghost" @click="toggleVoice" title="是否自动播放TTS">
          {{ settings.voiceEnabled ? '🔊 自动播放开' : '🔇 自动播放关' }}
        </button>
        <button class="btn ghost" @click="exportChat">导出</button>
        <button class="btn" :disabled="!canSave" @click="save">保存</button>
      </div>
    </ChatHeader>

    <LoginGate v-if="!isLogin" />

    <div class="chat-list">
      <!-- 始终传 text；assistant 打开 is-html 并传 Markdown-HTML -->
      <MessageBubble
        v-for="(m,i) in messages"
        :key="m.ts ?? i"
        :who="m.role==='user' ? 'user' : 'ai'"
        :avatar="m.role==='user' ? '👤' : (role.avatar || '🤖')"
        :text="m.role==='assistant' ? toHtml(m.content) : m.content"
        :is-html="m.role==='assistant'"
      >
        <template #meta>
          <span>{{ new Date(m.ts).toLocaleTimeString() }}</span>

          <!-- TTS 成功后可选择播放/不播放 -->
          <template v-if="m.role==='assistant'">
            <span v-if="m.audioUrl" style="margin-left:8px; opacity:.8;">WAV已生成</span>
            <button
              v-if="m.audioUrl && !isPlaying(m)"
              class="btn ghost"
              style="margin-left:8px"
              @click="play(m)"
            >▶ 播放</button>
            <button
              v-if="m.audioUrl && isPlaying(m)"
              class="btn ghost"
              style="margin-left:8px"
              @click="stop()"
            >■ 停止</button>
            <button
              v-if="m.audioUrl"
              class="btn ghost"
              style="margin-left:6px"
              @click="downloadFromUrl(m.audioUrl, `tts_${m.ts||Date.now()}.wav`)"
            >⬇️ 下载</button>
          </template>

          <a v-if="m.audioUrl" :href="m.audioUrl" target="_blank" style="margin-left:6px;">打开</a>
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
import { ref, watch, computed, onMounted } from 'vue'
import { useChatStore } from '../store/chat'
import { useUserStore } from '../store/user'
import { buildSystemPrompt } from '../utils/prompts'
import { chatStream, chatOnce } from '../api/llm'
import { asrFull } from '../api/asr'
import { synthesizeTTS } from '../api/tts'   // 走 /tts 代理，返回 Blob 或 {url, blob}
import AudioRecorder from '../components/AudioRecorder.vue'
import MessageBubble from '../components/MessageBubble.vue'
import DeepQuestionChips from '../components/DeepQuestionChips.vue'
import LoginGate from '../components/LoginGate.vue'
import TTSVoicePicker from '../components/TTSVoicePicker.vue'
import ChatHeader from '../components/ChatHeader.vue'
import MarkdownIt from 'markdown-it'

/* 多会话本地缓存（localStorage） */
import {
  listChats, createChat as createSession, deleteChat as deleteSession,
  loadChat as loadSession, saveChat as saveSession, renameChat
} from '../utils/chatCache'

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
const canSave = computed(()=> chat.messages.length>0)

/* Markdown 渲染器（最小配置） */
const md = new MarkdownIt({ html:false, linkify:true, breaks:true })
const toHtml = (t) => md.render(t || '')

/* 简单播放器：同一时间只播一个；是否播放由用户手动决定（或自动开关） */
const currentAudio = ref(null)
const currentUrl = ref('')
function isPlaying(m){ return !!currentAudio.value && currentUrl.value===m.audioUrl && !currentAudio.value.paused }
function play(m){
  try {
    if (!m?.audioUrl) return
    stop()
    currentUrl.value = m.audioUrl
    currentAudio.value = new Audio(m.audioUrl)
    currentAudio.value.onended = () => { currentAudio.value=null; currentUrl.value='' }
    currentAudio.value.play().catch(()=>{})
  } catch {}
}
function stop(){
  try { if (currentAudio.value){ currentAudio.value.pause(); currentAudio.value.currentTime=0 } } catch {}
  currentAudio.value = null
  currentUrl.value = ''
}
function downloadFromUrl(url, filename){
  const a = document.createElement('a')
  a.href = url; a.download = filename || `tts_${Date.now()}.wav`
  document.body.appendChild(a); a.click(); a.remove()
}

watch(tts, (v)=>{ chat.settings.ttsStyle=v.style; chat.settings.emoWeight=v.emoWeight }, { deep:true })

function parseDeepQuestions(text){
  const m = text.match(/\[DEEP_QUESTIONS\]([\s\S]*?)\[END\]/i)
  if(!m) return []
  const lines = m[1].split(/\n|\r/).map(s=>s.trim()).filter(Boolean)
  return lines.map(s=> s.replace(/^[-•\d\.\)\s]*/,'').trim()).filter(Boolean).slice(0,2)
}

async function onAudioDone(wav){
  const transcript = await asrFull(wav)
  chat.addMessage({ role:'user', content: transcript, ts: Date.now(), audioUrl: URL.createObjectURL(wav) })
  await converse(transcript)
}
function useQuestion(q){ text.value = q }

async function sendText(){
  if(!text.value.trim()) return
  const userText = text.value.trim()
  chat.addMessage({ role:'user', content: userText, ts: Date.now() })
  text.value = ''
  await converse(userText)
}

/* TTS：生成 WAV；根据开关决定是否自动播，默认仅挂URL由用户选择播放 */
async function doTTS(text, msgIndex){
  if (!text) return
  try {
    const res = await synthesizeTTS({
      text,
      style: chat.settings.ttsStyle,
      emoWeight: chat.settings.emoWeight,
      format: 'wav'
    })
    let url = null
    if (res instanceof Blob) url = URL.createObjectURL(res)
    else if (res?.url) url = res.url
    else if (res?.blob) url = URL.createObjectURL(res.blob)
    if (!url) return

    if (chat.messages[msgIndex]) {
      chat.messages[msgIndex].audioUrl = url
      if (settings.voiceEnabled) play(chat.messages[msgIndex])  // 自动播放可开关
    }
  } catch (e) {
    console.warn('TTS 失败：', e)
    chat.addMessage({ role:'assistant', content:`【系统】TTS失败：${e.message}`, ts: Date.now() })
  }
}

async function converse(userText) {
  chat.pending = true
  try {
    const system = buildSystemPrompt({
      role: role.value,
      memorySummary: chat.memorySummary,
      userPrefs: {}
    })
    const sysWithKB = chat.kbContext ? system + `\n\n【外部上下文，供参考】\n` + chat.kbContext : system

    let msgs = []
    if (user.isLogin) {
      msgs = [{ role:'system', content: sysWithKB }]
      for (const m of chat.messages) {
        if (m.role==='user' || m.role==='assistant') msgs.push({ role:m.role, content:m.content })
      }
      msgs.push({ role:'user', content:userText })
    } else {
      msgs = [{ role:'system', content: sysWithKB }, { role:'user', content:userText }]
    }

    let full = ''
    let aiIndex = -1

    if (settings.stream) {
      await chatStream({
        messages: msgs,
        onDelta: (delta) => {
          if (!full) {
            chat.addMessage({ role:'assistant', content: delta, ts: Date.now() })
            full = delta
            aiIndex = chat.messages.length - 1
          } else {
            full += delta
            chat.messages[aiIndex].content = full
          }
        },
        onDone: async () => {
          if (aiIndex >= 0) await doTTS(full, aiIndex)
          save()  // 本地保存
        }
      })
    } else {
      const content = await chatOnce(msgs)
      chat.addMessage({ role:'assistant', content, ts: Date.now() })
      full = content
      const idx = chat.messages.length - 1
      await doTTS(full, idx)
      save()
    }

    const qs = parseDeepQuestions(full)
    chat.setDeepQuestions(qs)

  } catch (e) {
    chat.addMessage({ role:'assistant', content: '【系统】对话失败：' + e.message, ts: Date.now() })
  } finally {
    chat.pending = false
  }
}

/* ============ 本地会话缓存：新建 / 删除 / 切换 / 自动保存（原地替换防止响应式引用丢失） ============ */
const chatList = ref(listChats())
const chatId = ref(chatList.value[0]?.id || '')

// 初始化：加载当前会话消息（原地写入）
onMounted(() => {
  if (!chatId.value) {
    const c = createSession(role.value?.name ? `${role.value.name} 的会话` : '新会话')
    chatList.value = listChats()
    chatId.value = c.id
  }
  const initMsgs = loadSession(chatId.value) || []
  chat.messages.splice(0, chat.messages.length, ...initMsgs)   // ✅ 原地替换
})

// 切换会话：原地替换
watch(chatId, (id) => {
  if (!id) return
  const msgs = loadSession(id) || []
  chat.messages.splice(0, chat.messages.length, ...msgs)       // ✅ 原地替换
})

// 自动保存（防抖）；建议 chatCache 仅保存 {role,content,ts}，不要持久化 audioUrl
let autosaveTimer = null
watch(() => chat.messages, (val) => {
  clearTimeout(autosaveTimer)
  autosaveTimer = setTimeout(() => {
    if (chatId.value) saveSession(chatId.value, val)
  }, 600)
}, { deep: true })

function newChat(){
  const c = createSession(role.value?.name ? `${role.value.name} 的会话` : '新会话')
  chatList.value = listChats()
  chatId.value = c.id
  chat.messages.splice(0, chat.messages.length)                 // 清空当前显示
}
function removeChat(){
  if (!chatId.value) return
  if (!confirm('确定删除当前会话？此操作不可恢复。')) return
  const id = chatId.value
  deleteSession(id)
  chatList.value = listChats()
  chatId.value = chatList.value[0]?.id || ''
  const msgs = chatId.value ? (loadSession(chatId.value) || []) : []
  chat.messages.splice(0, chat.messages.length, ...msgs)        // ✅
}
function save(){
  if (chatId.value) saveSession(chatId.value, chat.messages)
  console.info('已保存到本地：', chatId.value)
}
/* ================================================================================================= */

function exportChat(){
  const payload = { role: role.value, messages: chat.messages, ts: Date.now() }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type:'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `chat-${role.value.id}-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function toggleVoice(){ chat.settings.voiceEnabled = !chat.settings.voiceEnabled }
</script>

<style scoped>
/* Markdown 外观在 MessageBubble 内部 .content 中已有基础样式 */
</style>
