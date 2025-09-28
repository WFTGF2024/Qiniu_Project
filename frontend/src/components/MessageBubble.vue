<template>
  <div class="msg" :class="who">
    <div class="role">{{ avatar }}</div>
    <div>
      <div class="bubble" v-html="html"></div>
      <div class="meta">
        <slot name="meta"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  who: { type: String, default: 'ai' },
  text: { type: String, required: true },
  avatar: { type: String, default: '🤖' }
})
const html = computed(()=>{
  // very light markdown-ish
  let t = props.text
  t = t.replace(/\n\n/g, '<br/><br/>').replace(/\n/g, '<br/>' )
  return t
})
</script>