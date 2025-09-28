<template>
  <div class="card col" style="max-width:680px;margin:0 auto;">
    <b>注册</b>
    <div class="row">
      <input class="input" v-model="f.username" placeholder="用户名" style="flex:1" />
      <input class="input" v-model="f.full_name" placeholder="姓名" style="flex:1" />
    </div>
    <div class="row">
      <input class="input" type="password" v-model="f.password" placeholder="密码" style="flex:1" />
      <input class="input" v-model="f.email" placeholder="邮箱" style="flex:1" />
    </div>
    <div class="row">
      <input class="input" v-model="f.phone_number" placeholder="手机号" style="flex:1" />
    </div>
    <div class="row">
      <input class="input" v-model="f.security_question1" placeholder="密保问题1" style="flex:1" />
      <input class="input" v-model="f.security_answer1" placeholder="答案1" style="flex:1" />
    </div>
    <div class="row">
      <input class="input" v-model="f.security_question2" placeholder="密保问题2" style="flex:1" />
      <input class="input" v-model="f.security_answer2" placeholder="答案2" style="flex:1" />
    </div>
    <button class="btn" @click="submit">注册</button>
  </div>
</template>
<script setup>
import { reactive } from 'vue'
import { register } from '../api/core'
import { useRouter } from 'vue-router'

const router = useRouter()
const f = reactive({
  username: '', password: '', full_name: '', email:'', phone_number:'',
  security_question1:'你的第一所学校？', security_answer1:'',
  security_question2:'你最喜欢的书？', security_answer2:''
})

async function submit(){
  try{
    await register(f)
    alert('注册成功，请登录')
    router.push('/login')
  }catch(e){
    alert('注册失败：' + (e.response?.data?.message || e.message))
  }
}
</script>