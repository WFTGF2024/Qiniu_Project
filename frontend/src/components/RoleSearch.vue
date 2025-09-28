<template>
  <div class="col">
    <div class="search-box">
      <input class="input" v-model="q" placeholder="搜索角色：哈利波特、苏格拉底、面试官…" style="flex:1;" />
      <span class="badge">{{ filtered.length }}</span>
    </div>
    <div class="role-grid">
      <RoleCard v-for="r in filtered" :key="r.id" :role="r" @select="$emit('select', r)" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import roles from '../data/roles'
import RoleCard from './RoleCard.vue'

const q = ref('')
const filtered = computed(()=>{
  const s = q.value.trim().toLowerCase()
  if(!s) return roles
  return roles.filter(r=> (r.name + r.id).toLowerCase().includes(s))
})
</script>