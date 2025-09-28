<template>
  <div class="row" style="gap:6px;">
    <button class="btn" :disabled="recording" @click="start">🎙️ 开始</button>
    <button class="btn secondary" :disabled="!recording" @click="stop">⏹️ 停止</button>
    <span class="faint" v-if="recording">录音中… {{ seconds.toFixed(1) }}s</span>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { WavRecorder } from '../utils/wav-recorder'

const emit = defineEmits(['done', 'error'])

const rec = new WavRecorder({ targetSampleRate: 16000 })
const recording = ref(false)
const seconds = ref(0)
let timer = null

async function start(){
  try{
    await rec.start()
    recording.value = true
    seconds.value = 0
    timer = setInterval(()=>{ seconds.value += 0.1 }, 100)
  }catch(e){
    emit('error', e)
  }
}
async function stop(){
  try{
    const wav = await rec.stop()
    clearInterval(timer); timer = null
    recording.value = false
    emit('done', wav)
  }catch(e){
    emit('error', e)
  }
}
onBeforeUnmount(()=>{ if(timer) clearInterval(timer) })
</script>