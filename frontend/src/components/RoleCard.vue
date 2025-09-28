<template>
  <div class="role-card" @click="$emit('select')">
    <div class="role">{{ role.avatar || '🎭' }}</div>
    <div>
      <div><b>{{ role.name }}</b></div>
      <small class="hint">{{ role.id }}</small>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ role:Object })
</script>