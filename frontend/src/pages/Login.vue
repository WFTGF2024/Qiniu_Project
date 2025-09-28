<template>
  <div class="card col" style="max-width:480px;margin:0 auto;">
    <b>登录</b>
    <input class="input" v-model="username" placeholder="用户名" />
    <input class="input" type="password" v-model="password" placeholder="密码" />
    <button class="btn" @click="submit">登录</button>
    <div class="row">
      <small class="hint">没有账号？</small>
      <router-link to="/register">注册</router-link>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { login, me } from '../api/core'
import { useUserStore } from '../store/user'
import { useRouter } from 'vue-router'

const router = useRouter()
const user = useUserStore()
const username = ref('')
const password = ref('')

async function submit(){
  try{
    const { token } = await login({ username: username.value, password: password.value })
    user.setAuth(token, await me())
    router.push('/chat')
  }catch(e){
    alert('登录失败：' + (e.response?.data?.message || e.message))
  }
}
</script>