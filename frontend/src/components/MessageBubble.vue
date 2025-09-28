<template>
  <div class="message-bubble" :class="who">
    <div class="avatar">{{ avatar }}</div>
    <div class="body">
      <!-- ✅ 新增：当 isHtml 为 true 时，用 v-html 渲染；否则保持原来的纯文本 -->
      <div class="content" v-if="isHtml" v-html="text"></div>
      <div class="content" v-else>{{ text }}</div>

      <div class="meta"><slot name="meta" /></div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  text:   { type: String, required: true }, // 必填：无论纯文本还是 HTML 都传入这一项
  who:    { type: String,  default: 'ai'   }, // 'user' | 'ai'
  avatar: { type: String,  default: '🤖'   },
  // ✅ 新增：是否把 text 当作 HTML 渲染
  isHtml: { type: Boolean, default: false  },
})
</script>

<style scoped>
.message-bubble{ display:flex; gap:8px; margin:10px 12px; }
.message-bubble.user{ flex-direction: row-reverse; }
.avatar{ width:32px; height:32px; display:flex; align-items:center; justify-content:center; font-size:18px; }
.body{ max-width: 820px; }
.content{ white-space: pre-wrap; padding:10px 14px; border-radius:12px; background:#1f2937; color:#e5e7eb; }
.message-bubble.user .content{ background:#334155; }
.meta{ font-size:12px; opacity:.8; margin-top:6px; }

/* 让 Markdown 看起来更舒服（可删） */
.content :deep(p){ margin:.4rem 0; }
.content :deep(ul), .content :deep(ol){ padding-left:1.2rem; margin:.4rem 0; }
.content :deep(code){ padding:.1rem .3rem; border-radius:4px; background:rgba(0,0,0,.1); }
.content :deep(pre){ padding:.6rem; border-radius:8px; background:rgba(0,0,0,.1); overflow:auto; }
</style>
