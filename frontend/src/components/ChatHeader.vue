<template>
  <div class="row" style="justify-content:space-between">
    <div class="row">
      <span class="badge">{{ role.name }}</span>
      <small class="hint">{{ role.id }}</small>
    </div>
    <slot />
  </div>
</template>
<script setup>
defineProps({ role:Object })
</script>