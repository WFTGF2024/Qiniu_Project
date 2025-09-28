<template>
  <div class="deep-questions" v-if="items && items.length">
    <div v-for="(x,i) in items" :key="i" class="chip" @click="$emit('pick', x)">💡 {{ x }}</div>
  </div>
</template>
<script setup>
defineProps({ items: Array })
</script>