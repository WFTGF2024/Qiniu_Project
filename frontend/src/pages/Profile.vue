<template>
  <div class="card col" style="max-width:640px;">
    <div class="row" style="justify-content:space-between;">
      <b>账户</b>
      <div class="row">
        <router-link class="btn ghost" to="/login" v-if="!user.isLogin">登录</router-link>
        <button class="btn danger" @click="logout" v-else>退出</button>
      </div>
    </div>
    <div v-if="user.isLogin">
      <pre style="white-space:pre-wrap;">{{ JSON.stringify(user.user, null, 2) }}</pre>
    </div>
    <small class="hint">免登录体验：不保存历史与个性化；登录后开启聊天记录保存、会员与订单。</small>
  </div>
</template>
<script setup>
import { useUserStore } from '../store/user'
const user = useUserStore()
function logout(){ user.logout() }
</script>