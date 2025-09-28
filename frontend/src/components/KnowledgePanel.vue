<template>
  <div class="col">
    <div class="row" style="justify-content:space-between;">
      <b>知识面板</b>
      <span class="faint">用于检索/注入上下文</span>
    </div>
    <div class="card col">
      <div class="row">
        <input class="input" v-model="url" placeholder="粘贴网页 URL，入库并切块" style="flex:1;" />
        <button class="btn" @click="ingest">入库</button>
      </div>
      <small class="hint">抓取 → 清洗 → 切块 → 向量化 → Qdrant 检索</small>
      <small class="hint" v-if="ingested">已入库：{{ ingested.title }}</small>
    </div>

    <div class="card col">
      <div class="row">
        <input class="input" v-model="q" placeholder="在已入库网页中搜索" style="flex:1;" />
        <button class="btn secondary" @click="search">搜索</button>
      </div>
      <div v-if="results.length" class="col" style="max-height:320px;overflow:auto;">
        <div v-for="r in results" :key="r.page_id" class="card" style="padding:8px;">
          <div><b>{{ r.title }}</b></div>
          <small class="hint">{{ r.url }}</small>
          <div style="font-size:12px;margin-top:6px;">{{ r.snippet }}</div>
          <button class="btn ghost" style="margin-top:6px;" @click="addToContext(r)">加入上下文</button>
        </div>
      </div>
      <button class="btn" v-if="contextText" @click="inject">注入到下一轮</button>
      <small v-if="contextText" class="hint">将把下列片段注入系统提示：{{ shortContext }}</small>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ingestUrl, webSearch } from '../api/websearch'
import { useChatStore } from '../store/chat'

const url = ref('')
const q = ref('')
const ingested = ref(null)
const results = ref([])
const ctxPieces = ref([])
const chat = useChatStore()

const contextText = computed(()=> ctxPieces.value.map(x=> x.snippet || '').join('\n---\n') )
const shortContext = computed(()=> contextText.value.slice(0, 120) + (contextText.value.length>120?'…':''))

async function ingest(){
  if(!url.value) return
  ingested.value = await ingestUrl(url.value)
}
async function search(){
  if(!q.value) return
  const data = await webSearch({ q: q.value, top_k: 5, mode:'hybrid', alpha: 0.6 })
  results.value = data.results || []
}
function addToContext(r){
  ctxPieces.value.push(r)
}
function inject(){
  chat.setKbContext(contextText.value)
  ctxPieces.value = []
}
</script>