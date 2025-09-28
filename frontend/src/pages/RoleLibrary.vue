<template>
  <div class="col">
    <div class="row" style="justify-content:space-between;align-items:center;">
      <b>角色库</b>
      <router-link class="btn ghost" to="/chat">返回对话</router-link>
    </div>
    <hr class="sep"/>
    <RoleSearch @select="onSelectRole" />
  </div>
</template>
<script setup>
import RoleSearch from '../components/RoleSearch.vue'
import { useChatStore } from '../store/chat'
import { useRouter } from 'vue-router'

const chat = useChatStore()
const router = useRouter()
function onSelectRole(r){
  chat.setCurrentRole(r)
  router.push('/chat')
}
</script>