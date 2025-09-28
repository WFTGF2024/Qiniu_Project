<template>
  <div class="col">
    <div class="row" style="justify-content:space-between;align-items:center;">
      <b>会员</b>
      <router-link class="btn ghost" to="/profile">账号</router-link>
    </div>
    <div class="card col">
      <div class="row" v-if="!user.isLogin">
        <small class="hint">登录后可查看会员信息与订单。</small>
        <router-link to="/login" class="btn">去登录</router-link>
      </div>
      <template v-else>
        <div class="row" style="gap:16px; align-items:center;">
          <button class="btn" @click="refresh">刷新</button>
          <button class="btn secondary" @click="buy">购买月度会员（¥29）</button>
        </div>
        <div class="card">
          <b>当前会员</b>
          <pre style="white-space:pre-wrap;">{{ JSON.stringify(membership, null, 2) }}</pre>
        </div>
        <div class="card">
          <b>历史订单</b>
          <pre style="white-space:pre-wrap;">{{ JSON.stringify(orders, null, 2) }}</pre>
        </div>
      </template>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useUserStore } from '../store/user'
import { getMembership, listOrders, createOrder } from '../api/core'

const user = useUserStore()
const membership = ref(null)
const orders = ref([])

async function refresh(){
  try{
    membership.value = await getMembership(user.user.user_id)
  }catch{ membership.value = null }
  try{
    orders.value = await listOrders(user.user.user_id)
  }catch{ orders.value = [] }
}
async function buy(){
  const data = await createOrder({ user_id: user.user.user_id, duration_months: 1, amount: 29, payment_method: 'wechat' })
  alert('下单成功：' + JSON.stringify(data))
  refresh()
}
</script>