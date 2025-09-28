<template>
  <div class="row">
    <label>音色：</label>
    <select class="input" v-model="style">
      <option value="style1">风格一</option>
      <option value="style2">风格二</option>
      <option value="style3">风格三</option>
    </select>
    <label>情感强度：</label>
    <input type="range" min="0" max="1" step="0.05" v-model.number="emo" />
    <span class="badge">{{ emo.toFixed(2) }}</span>
  </div>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ modelValue: Object })
const emit = defineEmits(['update:modelValue'])
const style = computed({
  get: ()=> props.modelValue?.style || 'style1',
  set: (v)=> emit('update:modelValue', { ...props.modelValue, style: v })
})
const emo = computed({
  get: ()=> props.modelValue?.emoWeight ?? 0.65,
  set: (v)=> emit('update:modelValue', { ...props.modelValue, emoWeight: Number(v) })
})
</script>