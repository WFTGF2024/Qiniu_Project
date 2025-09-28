<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RoleSearch @select="onSelectRole" />
      <hr class="sep" />
      <router-link class="role-card" to="/chat">
        <div class="role">💬</div>
        <div>
          <div><b>对话</b></div>
          <small class="hint">语音/文字，角色扮演</small>
        </div>
      </router-link>
      <router-link class="role-card" to="/membership">
        <div class="role">⭐</div>
        <div>
          <div><b>会员</b></div>
          <small class="hint">查看权益与订单</small>
        </div>
      </router-link>
      <router-link class="role-card" to="/profile">
        <div class="role">👤</div>
        <div>
          <div><b>账户</b></div>
          <small class="hint">登录/注册/资料</small>
        </div>
      </router-link>
    </aside>

    <header class="header">
      <div class="row">
        <span class="badge">{{ appName }}</span>
        <span class="faint">莫兰迪配色 · 统一语音交互平台</span>
      </div>
      <div class="row">
        <router-link class="btn ghost" to="/role">角色库</router-link>
        <router-link class="btn ghost" to="/chat">聊天</router-link>
        <router-link class="btn ghost" to="/membership">会员</router-link>
      </div>
    </header>

    <main class="main">
      <router-view />
    </main>

    <aside class="right">
      <KnowledgePanel />
    </aside>
  </div>
</template>

<script setup>
import RoleSearch from './components/RoleSearch.vue'
import KnowledgePanel from './components/KnowledgePanel.vue'
import { useRouter } from 'vue-router'
import { useChatStore } from './store/chat'
const router = useRouter()
const appName = import.meta.env.VITE_APP_NAME || 'AI 角色扮演'
const chat = useChatStore()

function onSelectRole(role){
  chat.setCurrentRole(role)
  router.push('/chat')
}
</script>